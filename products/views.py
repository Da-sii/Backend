from rest_framework import generics, parsers
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import NotFound, ValidationError
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Sum, Count, Q, Subquery
from django.db.models.functions import Coalesce
from products.models import Product, BigCategory, SmallCategory, ProductIngredient, ProductImage, Ingredient, CategoryProduct
from products.serializers import ProductCreateSerializer, ProductReadSerializer, ProductDetailSerializer, ProductRankingSerializer
from products.serializers import ProductsListSerializer, CategorySerializer, ProductSearchSerializer, MainSerializer
from products.utils import record_view, upload_images_to_s3

# 템플릿 뷰를 위한 import 추가
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponseForbidden

# 제품 등록
class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductCreateSerializer
    permission_classes = [AllowAny]  # 인증 없이 접근 가능
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def create(self, request, *args, **kwargs):
        create_serializer = self.get_serializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        product = create_serializer.save()

        read_serializer = ProductReadSerializer(product)
        
        return Response({"success": True, "product": read_serializer.data}, status=201)

    @extend_schema(
        summary="제품 등록",
        tags=["제품"]
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

# 제품 상세 (GET /products/<id>/)
class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "id"

    @extend_schema(
        summary="제품 상세 조회",
        tags=["제품"]
    )
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

# 제품 랭킹 (GET /products/ranking/)
class ProductRankingView(generics.ListAPIView):
    serializer_class = ProductRankingSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        today = timezone.now().date()
        start_date = today - timedelta(days=30)

        # 최근 30일간의 일일 조회수 합계를 기준으로 랭킹
        queryset = Product.objects.annotate(
            total_views=Coalesce(
                Sum('daily_views__views', filter=Q(daily_views__date__gte=start_date)),
                0
            )
        ).order_by('-total_views')[:10]

        return queryset

    @extend_schema(
        summary="제품 랭킹 조회",
        tags=["제품"]
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

# 제품 목록 (GET /products/list/)
class ProductListView(generics.ListAPIView):
    serializer_class = ProductsListSerializer
    permission_classes = [AllowAny]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        queryset = Product.objects.all()
        
        # 검색 파라미터
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(company__icontains=search)
            )
        
        return queryset.order_by('-id')

    @extend_schema(
        summary="제품 목록 조회",
        tags=["제품"]
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

# 카테고리별 제품 조회 (GET /products/category/)
class ProductCategoryView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return BigCategory.objects.prefetch_related('smallCategories__category_products__product').all()

    @extend_schema(
        summary="카테고리별 제품 조회",
        tags=["제품"]
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

# 제품 검색 (GET /products/search/)
class ProductSearchView(generics.ListAPIView):
    serializer_class = ProductSearchSerializer
    permission_classes = [AllowAny]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        queryset = Product.objects.all()
        
        keyword = self.request.query_params.get('keyword', '')
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword) | 
                Q(company__icontains=keyword) |
                Q(ingredients__ingredient__name__icontains=keyword)
            ).distinct()
        
        return queryset.order_by('-id')

    @extend_schema(
        summary="제품 검색",
        tags=["제품"],
        parameters=[
            OpenApiParameter(
                name='keyword',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='검색 키워드'
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

# 메인 페이지 (GET /products/main/)
class MainView(generics.ListAPIView):
    serializer_class = MainSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        today = timezone.now().date()
        start_date = today - timedelta(days=7)

        # 최근 7일간 인기 제품
        popular_products = Product.objects.annotate(
            recent_views=Coalesce(
                Sum('daily_views__views', filter=Q(daily_views__date__gte=start_date)),
                0
            )
        ).order_by('-recent_views')[:8]

        return popular_products

    @extend_schema(
        summary="메인 페이지 조회",
        tags=["제품"]
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

# 제품 이미지 업로드 (POST /products/<id>/images/)
class UploadProductImageView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    @extend_schema(
        summary="제품 이미지 업로드",
        tags=["제품"]
    )
    def post(self, request, id):
        try:
            product = Product.objects.get(id=id)
        except Product.DoesNotExist:
            raise NotFound("제품을 찾을 수 없습니다.")
        
        images = request.FILES.getlist('images')
        
        if not images:
            raise ValidationError("이미지 파일이 필요합니다.")
        
        # S3 업로드 및 ProductImage 저장
        uploaded_images = upload_images_to_s3(product, images)
        ProductImage.objects.bulk_create(uploaded_images)
        
        return Response({"success": True, "message": f"{len(uploaded_images)}개의 이미지가 등록되었습니다."}, status=201)

# BigCategory 입력 화면 (템플릿 기반)
def big_category_form(request):
    """BigCategory 데이터 입력 화면 - 개발 환경에서만 접근 가능"""
    # 운영 환경에서는 접근 차단
    if settings.DJANGO_ENV == 'production':
        return HttpResponseForbidden("이 페이지는 개발 환경에서만 접근 가능합니다.")
    
    if request.method == 'POST':
        category = request.POST.get('category', '').strip()
        
        if category:
            BigCategory.objects.create(category=category)
            messages.success(request, f'"{category}" 카테고리가 성공적으로 추가되었습니다.')
            return redirect('big_category_form')
        else:
            messages.error(request, '카테고리 이름을 입력해주세요.')
    
    # 기존 카테고리 목록 가져오기
    categories = BigCategory.objects.all().order_by('id')
    
    return render(request, 'products/big_category_form.html', {
        'categories': categories
    })

# SmallCategory 입력 화면 (템플릿 기반)
def small_category_form(request):
    """SmallCategory 데이터 입력 화면 - 개발 환경에서만 접근 가능"""
    # 운영 환경에서는 접근 차단
    if settings.DJANGO_ENV == 'production':
        return HttpResponseForbidden("이 페이지는 개발 환경에서만 접근 가능합니다.")
    
    if request.method == 'POST':
        big_category_id = request.POST.get('bigCategory', '').strip()
        category = request.POST.get('category', '').strip()
        
        if not big_category_id:
            messages.error(request, '대분류를 선택해주세요.')
        elif not category:
            messages.error(request, '소분류 이름을 입력해주세요.')
        else:
            try:
                big_category = BigCategory.objects.get(id=big_category_id)
                SmallCategory.objects.create(
                    bigCategory=big_category,
                    category=category
                )
                messages.success(request, f'"{big_category.category} - {category}" 소분류가 성공적으로 추가되었습니다.')
                return redirect('small_category_form')
            except BigCategory.DoesNotExist:
                messages.error(request, '선택한 대분류를 찾을 수 없습니다.')
    
    # 기존 데이터 가져오기
    big_categories = BigCategory.objects.all().order_by('id')
    small_categories = SmallCategory.objects.select_related('bigCategory').all().order_by('bigCategory__id', 'id')
    
    return render(request, 'products/small_category_form.html', {
        'big_categories': big_categories,
        'small_categories': small_categories
    })

# Product 입력 화면 (템플릿 기반)
def product_form(request):
    """Product 데이터 입력 화면 - 개발 환경에서만 접근 가능"""
    # 운영 환경에서는 접근 차단
    if settings.DJANGO_ENV == 'production':
        return HttpResponseForbidden("이 페이지는 개발 환경에서만 접근 가능합니다.")
    
    if request.method == 'POST':
        # 기본 정보
        name = request.POST.get('name', '').strip()
        company = request.POST.get('company', '').strip()
        price = request.POST.get('price', '').strip()
        unit = request.POST.get('unit', '').strip()
        piece = request.POST.get('piece', '').strip()
        product_type = request.POST.get('productType', '').strip()
        
        # 필수 필드 검증
        if not all([name, company, price, unit, piece, product_type]):
            messages.error(request, '모든 필수 항목을 입력해주세요.')
        else:
            try:
                # Product 생성
                product = Product.objects.create(
                    name=name,
                    company=company,
                    price=int(price),
                    unit=unit,
                    piece=piece,
                    productType=product_type
                )
                
                # 이미지 URL들 추가
                image_urls = request.POST.getlist('image_urls[]')
                for url in image_urls:
                    url = url.strip()
                    if url:
                        ProductImage.objects.create(product=product, url=url)
                
                # 성분들 추가
                ingredient_ids = request.POST.getlist('ingredient_ids[]')
                amounts = request.POST.getlist('amounts[]')
                for ingredient_id, amount in zip(ingredient_ids, amounts):
                    ingredient_id = ingredient_id.strip()
                    amount = amount.strip()
                    if ingredient_id and amount:
                        try:
                            ingredient = Ingredient.objects.get(id=ingredient_id)
                            ProductIngredient.objects.create(
                                product=product,
                                ingredient=ingredient,
                                amount=amount
                            )
                        except Ingredient.DoesNotExist:
                            pass
                
                # 카테고리들 추가
                category_ids = request.POST.getlist('category_ids[]')
                for category_id in category_ids:
                    category_id = category_id.strip()
                    if category_id:
                        try:
                            category = SmallCategory.objects.get(id=category_id)
                            CategoryProduct.objects.create(
                                product=product,
                                category=category
                            )
                        except SmallCategory.DoesNotExist:
                            pass
                
                messages.success(request, f'"{name}" 제품이 성공적으로 추가되었습니다.')
                return redirect('product_form')
            except ValueError:
                messages.error(request, '가격은 숫자로 입력해주세요.')
            except Exception as e:
                messages.error(request, f'오류가 발생했습니다: {str(e)}')
    
    # 기존 데이터 가져오기
    ingredients = Ingredient.objects.all().order_by('name')
    small_categories = SmallCategory.objects.select_related('bigCategory').all().order_by('bigCategory__id', 'id')
    # 제품 정보를 더 자세히 가져오기 (이미지, 성분, 카테고리 개수 포함)
    products = Product.objects.prefetch_related(
        'images',
        'ingredients',
        'category_products__category__bigCategory'
    ).annotate(
        image_count=Count('images'),
        ingredient_count=Count('ingredients')
    ).order_by('-id')[:20]  # 최근 20개만 표시
    
    return render(request, 'products/product_form.html', {
        'ingredients': ingredients,
        'small_categories': small_categories,
        'products': products
    })

# Ingredient 입력 화면 (템플릿 기반)
def ingredient_form(request):
    """Ingredient 데이터 입력 화면 - 개발 환경에서만 접근 가능"""
    # 운영 환경에서는 접근 차단
    if settings.DJANGO_ENV == 'production':
        return HttpResponseForbidden("이 페이지는 개발 환경에서만 접근 가능합니다.")
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        english_ingredient = request.POST.get('englishIngredient', '').strip()
        min_recommended = request.POST.get('minRecommended', '').strip()
        max_recommended = request.POST.get('maxRecommended', '').strip()
        effect = request.POST.get('effect', '').strip()
        side_effect = request.POST.get('sideEffect', '').strip()
        
        # 필수 필드 검증
        if not all([name, english_ingredient, min_recommended, max_recommended, effect]):
            messages.error(request, '필수 항목을 모두 입력해주세요.')
        else:
            Ingredient.objects.create(
                name=name,
                englishIngredient=english_ingredient,
                minRecommended=min_recommended,
                maxRecommended=max_recommended,
                effect=effect,
                sideEffect=side_effect if side_effect else None
            )
            messages.success(request, f'"{name}" 성분이 성공적으로 추가되었습니다.')
            return redirect('ingredient_form')
    
    # 기존 성분 목록 가져오기
    ingredients = Ingredient.objects.all().order_by('name')
    
    return render(request, 'products/ingredient_form.html', {
        'ingredients': ingredients
    })

# Product 수정 화면 (템플릿 기반)
def product_edit(request, product_id):
    """Product 데이터 수정 화면 - 개발 환경에서만 접근 가능"""
    # 운영 환경에서는 접근 차단
    if settings.DJANGO_ENV == 'production':
        return HttpResponseForbidden("이 페이지는 개발 환경에서만 접근 가능합니다.")
    
    try:
        product = Product.objects.prefetch_related(
            'images',
            'ingredients__ingredient',
            'category_products__category__bigCategory'
        ).get(id=product_id)
    except Product.DoesNotExist:
        messages.error(request, '제품을 찾을 수 없습니다.')
        return redirect('product_form')
    
    if request.method == 'POST':
        # 기본 정보 수정
        product.name = request.POST.get('name', '').strip()
        product.company = request.POST.get('company', '').strip()
        product.unit = request.POST.get('unit', '').strip()
        product.piece = request.POST.get('piece', '').strip()
        product.productType = request.POST.get('productType', '').strip()
        
        try:
            product.price = int(request.POST.get('price', 0))
        except ValueError:
            messages.error(request, '가격은 숫자로 입력해주세요.')
            return redirect('product_edit', product_id=product_id)
        
        # 필수 필드 검증
        if not all([product.name, product.company, product.unit, product.piece, product.productType]):
            messages.error(request, '모든 필수 항목을 입력해주세요.')
        else:
            product.save()
            
            # 기존 이미지 삭제 처리
            delete_image_ids = request.POST.getlist('delete_image_ids[]')
            if delete_image_ids:
                ProductImage.objects.filter(id__in=delete_image_ids, product=product).delete()
            
            # 새 이미지 URL 추가
            new_image_urls = request.POST.getlist('new_image_urls[]')
            for url in new_image_urls:
                url = url.strip()
                if url:
                    ProductImage.objects.create(product=product, url=url)
            
            # 기존 성분 삭제 처리
            delete_ingredient_ids = request.POST.getlist('delete_ingredient_ids[]')
            if delete_ingredient_ids:
                ProductIngredient.objects.filter(id__in=delete_ingredient_ids, product=product).delete()
            
            # 기존 성분 수정
            existing_product_ingredient_ids = request.POST.getlist('existing_product_ingredient_ids[]')
            existing_ingredient_ids = request.POST.getlist('existing_ingredient_ids[]')
            existing_amounts = request.POST.getlist('existing_amounts[]')
            for prod_ing_id, ing_id, amount in zip(existing_product_ingredient_ids, existing_ingredient_ids, existing_amounts):
                prod_ing_id = prod_ing_id.strip()
                ing_id = ing_id.strip()
                amount = amount.strip()
                if prod_ing_id and ing_id and amount:
                    try:
                        product_ing = ProductIngredient.objects.get(id=prod_ing_id, product=product)
                        ingredient = Ingredient.objects.get(id=ing_id)
                        product_ing.ingredient = ingredient
                        product_ing.amount = amount
                        product_ing.save()
                    except (ProductIngredient.DoesNotExist, Ingredient.DoesNotExist):
                        pass
            
            # 새 성분 추가
            new_ingredient_ids = request.POST.getlist('new_ingredient_ids[]')
            new_amounts = request.POST.getlist('new_amounts[]')
            for ingredient_id, amount in zip(new_ingredient_ids, new_amounts):
                ingredient_id = ingredient_id.strip()
                amount = amount.strip()
                if ingredient_id and amount:
                    try:
                        ingredient = Ingredient.objects.get(id=ingredient_id)
                        ProductIngredient.objects.create(
                            product=product,
                            ingredient=ingredient,
                            amount=amount
                        )
                    except Ingredient.DoesNotExist:
                        pass
            
            # 기존 카테고리 삭제 처리
            delete_category_ids = request.POST.getlist('delete_category_ids[]')
            if delete_category_ids:
                CategoryProduct.objects.filter(id__in=delete_category_ids, product=product).delete()
            
            # 새 카테고리 추가
            new_category_ids = request.POST.getlist('new_category_ids[]')
            for category_id in new_category_ids:
                category_id = category_id.strip()
                if category_id:
                    try:
                        category = SmallCategory.objects.get(id=category_id)
                        # 중복 체크
                        if not CategoryProduct.objects.filter(product=product, category=category).exists():
                            CategoryProduct.objects.create(
                                product=product,
                                category=category
                            )
                    except SmallCategory.DoesNotExist:
                        pass
            
            messages.success(request, f'"{product.name}" 제품이 성공적으로 수정되었습니다.')
            return redirect('product_form')
    
    # 기존 데이터 가져오기
    ingredients = Ingredient.objects.all().order_by('name')
    small_categories = SmallCategory.objects.select_related('bigCategory').all().order_by('bigCategory__id', 'id')
    
    return render(request, 'products/product_edit.html', {
        'product': product,
        'ingredients': ingredients,
        'small_categories': small_categories
    })
