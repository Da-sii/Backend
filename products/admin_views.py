# 관리자용 템플릿 뷰
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count
from products.models import Product, BigCategory, MiddleCategory, SmallCategory, ProductIngredient, ProductImage, \
    Ingredient, \
    CategoryProduct, OtherIngredient, ProductOtherIngredient, ProductRequest, IngredientGuide
from products.utils import upload_images_to_s3
from django.conf import settings
import json

# BigCategory 입력 화면 (템플릿 기반)
def big_category_form(request):
    """BigCategory 데이터 입력 화면"""
    
    if request.method == 'POST':
        category = request.POST.get('category', '').strip()
        
        if category:
            BigCategory.objects.create(category=category)
            messages.success(request, f'"{category}" 카테고리가 성공적으로 추가되었습니다.')
            return redirect('admin_big_category_form')
        else:
            messages.error(request, '카테고리 이름을 입력해주세요.')
    
    # 기존 카테고리 목록 가져오기
    categories = BigCategory.objects.all().order_by('id')
    
    return render(request, 'products/big_category_form.html', {
        'categories': categories
    })

def big_category_edit(request, category_id):
    """BigCategory 수정 화면"""
    try:
        category = BigCategory.objects.get(id=category_id)
    except BigCategory.DoesNotExist:
        messages.error(request, '대분류를 찾을 수 없습니다.')
        return redirect('admin_big_category_form')

    if request.method == 'POST':
        category_name = request.POST.get('category', '').strip()
        
        if not category_name:
            messages.error(request, '카테고리 이름을 입력해주세요.')
        else:
            category.category = category_name
            category.save()
            messages.success(request, f'"{category_name}" 대분류가 성공적으로 수정되었습니다.')
            return redirect('admin_big_category_form')

    return render(request, 'products/big_category_edit.html', {
        'category': category
    })

# MiddleCategory 입력 화면 (템플릿 기반)
def middle_category_form(request):
    if request.method == 'POST':
        big_category_id = request.POST.get('bigCategory', '').strip()
        category = request.POST.get('category', '').strip()

        if not big_category_id:
            messages.error(request, '대분류를 선택해주세요.')
        elif not category:
            messages.error(request, '중분류 이름을 입력해주세요.')
        else:
            try:
                big_category = BigCategory.objects.get(id=big_category_id)
                MiddleCategory.objects.create(
                    big_category=big_category,
                    category=category
                )
                messages.success(
                    request,
                    f'"{big_category.category} - {category}" 중분류가 추가되었습니다.'
                )
                return redirect('admin_middle_category_form')
            except BigCategory.DoesNotExist:
                messages.error(request, '선택한 대분류를 찾을 수 없습니다.')

    big_categories = BigCategory.objects.all().order_by('id')
    middle_categories = MiddleCategory.objects.select_related(
        'big_category'
    ).order_by('big_category__id', 'id')

    return render(request, 'products/middle_category_form.html', {
        'big_categories': big_categories,
        'middle_categories': middle_categories,
    })

def middle_category_edit(request, category_id):
    try:
        middle_category = MiddleCategory.objects.select_related(
            'big_category'
        ).get(id=category_id)
    except MiddleCategory.DoesNotExist:
        messages.error(request, '중분류를 찾을 수 없습니다.')
        return redirect('admin_middle_category_form')

    if request.method == 'POST':
        big_category_id = request.POST.get('bigCategory', '').strip()
        category_name = request.POST.get('category', '').strip()

        if not big_category_id:
            messages.error(request, '대분류를 선택해주세요.')
        elif not category_name:
            messages.error(request, '중분류 이름을 입력해주세요.')
        else:
            try:
                big_category = BigCategory.objects.get(id=big_category_id)
                middle_category.big_category = big_category
                middle_category.category = category_name
                middle_category.save()

                messages.success(
                    request,
                    f'"{big_category.category} - {category_name}" 중분류가 수정되었습니다.'
                )
                return redirect('admin_middle_category_form')

            except BigCategory.DoesNotExist:
                messages.error(request, '선택한 대분류를 찾을 수 없습니다.')

    big_categories = BigCategory.objects.all().order_by('id')

    return render(request, 'products/middle_category_edit.html', {
        'middle_category': middle_category,
        'big_categories': big_categories,
    })

def middle_category_delete(request, category_id):
    try:
        middle_category = MiddleCategory.objects.get(id=category_id)
    except MiddleCategory.DoesNotExist:
        messages.error(request, '중분류를 찾을 수 없습니다.')
        return redirect('admin_middle_category_form')

    if request.method == 'POST':
        category_name = middle_category.category

        # 🔥 중요: 연결된 소분류가 있으면 먼저 정리
        SmallCategory.objects.filter(
            middle_category=middle_category
        ).delete()

        middle_category.delete()

        messages.success(
            request,
            f'"{category_name}" 중분류가 삭제되었습니다.'
        )
        return redirect('admin_middle_category_form')

    return render(request, 'products/middle_category_delete_confirm.html', {
        'middle_category': middle_category
    })

# SmallCategory 입력 화면 (템플릿 기반)
def small_category_form(request):
    """SmallCategory 데이터 입력 화면"""
    
    if request.method == 'POST':
        middle_category_id = request.POST.get('middleCategory', '').strip()
        category = request.POST.get('category', '').strip()

        if not middle_category_id:
            messages.error(request, '중분류를 선택해주세요.')
        elif not category:
            messages.error(request, '소분류 이름을 입력해주세요.')
        else:
            try:
                middle_category = MiddleCategory.objects.get(id=middle_category_id)

                SmallCategory.objects.create(
                    middle_category=middle_category,
                    category=category
                )

                messages.success(
                    request,
                    f'"{middle_category.big_category.category} - '
                    f'{middle_category.category} - {category}" '
                    '소분류가 성공적으로 추가되었습니다.'
                )
                return redirect('admin_small_category_form')

            except MiddleCategory.DoesNotExist:
                messages.error(request, '선택한 중분류를 찾을 수 없습니다.')
    
    # 기존 데이터 가져오기
    middle_categories = MiddleCategory.objects.select_related(
        'big_category'
    ).order_by('big_category__id', 'id')
    small_categories = SmallCategory.objects.select_related(
        'middle_category__big_category'
    ).order_by(
        'middle_category__big_category__id',
        'middle_category__id',
        'id'
    )

    return render(request, 'products/small_category_form.html', {
        'middle_categories': middle_categories,
        'small_categories': small_categories
    })

def small_category_edit(request, category_id):
    """SmallCategory 수정 화면"""
    try:
        small_category = SmallCategory.objects.select_related(
            'middle_category__big_category'
        ).get(id=category_id)
    except SmallCategory.DoesNotExist:
        messages.error(request, '소분류를 찾을 수 없습니다.')
        return redirect('admin_small_category_form')

    if request.method == 'POST':
        middle_category_id = request.POST.get('middleCategory', '').strip()
        category_name = request.POST.get('category', '').strip()

        if not middle_category_id:
            messages.error(request, '중분류를 선택해주세요.')
        elif not category_name:
            messages.error(request, '소분류 이름을 입력해주세요.')
        else:
            try:
                middle_category = MiddleCategory.objects.get(id=middle_category_id)

                small_category.middle_category = middle_category
                small_category.category = category_name
                small_category.save()

                messages.success(
                    request,
                    f'"{middle_category.big_category.category} - '
                    f'{middle_category.category} - {category_name}" '
                    '소분류가 성공적으로 수정되었습니다.'
                )
                return redirect('admin_small_category_form')

            except MiddleCategory.DoesNotExist:
                messages.error(request, '선택한 중분류를 찾을 수 없습니다.')

    # GET 요청 시 화면에 뿌릴 데이터
    big_categories = BigCategory.objects.all().order_by('id')
    middle_categories = MiddleCategory.objects.select_related(
        'big_category'
    ).all().order_by('big_category__id', 'id')

    return render(request, 'products/small_category_edit.html', {
        'small_category': small_category,
        'middle_categories': middle_categories,
    })

# Product 입력 화면 (템플릿 기반)
@transaction.atomic
def product_form(request):
    """Product 데이터 입력 화면"""
    
    if request.method == 'POST':
        # 기본 정보
        name = request.POST.get('name', '').strip()
        company = request.POST.get('company', '').strip()
        product_type = request.POST.get('productType', '').strip()
        coupang_raw = request.POST.get('coupang', '').strip()
        coupang = coupang_raw or None
        
        # 필수 필드 검증
        if not all([name, company, product_type]):
            messages.error(request, '모든 필수 항목을 입력해주세요.')
        else:
            try:
                # Product 생성
                product = Product.objects.create(
                    name=name,
                    company=company,
                    productType=product_type,
                    coupang=coupang
                )
                
                # 이미지 파일 처리
                image_files = request.FILES.getlist('image_files')
                
                if image_files:
                    uploaded_images = upload_images_to_s3(product, image_files)
                    ProductImage.objects.bulk_create(uploaded_images)
                
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

                # 기타 원료들 추가
                other_ingredient_ids = request.POST.getlist('other_ingredient_ids[]')
                for oi_id in other_ingredient_ids:
                    oi_id = oi_id.strip()
                    if oi_id:
                        try:
                            oi = OtherIngredient.objects.get(id=oi_id)
                            ProductOtherIngredient.objects.create(
                                product=product,
                                other_ingredient=oi
                            )
                        except OtherIngredient.DoesNotExist:
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
                return redirect('admin_product_form')
            except ValueError:
                messages.error(request, '가격은 숫자로 입력해주세요.')
            except Exception as e:
                messages.error(request, f'오류가 발생했습니다: {str(e)}')
    
    # 기존 데이터 가져오기
    ingredients = Ingredient.objects.all().order_by('id')
    small_categories = SmallCategory.objects.select_related('middle_category__big_category').all().order_by(
        'middle_category__big_category__id',
        'middle_category__id',
        'id'
    )
    other_ingredients = OtherIngredient.objects.all().order_by("name")

    # 제품 정보를 더 자세히 가져오기 (이미지, 성분, 카테고리 개수 포함)
    products = Product.objects.annotate(
        image_count=Count('images', distinct=True),
        ingredient_count=Count('ingredients', distinct=True),
        category_count=Count('category_products', distinct=True)
    ).prefetch_related(
        'images',
        'ingredients',
        'category_products__category__middle_category__big_category',
        'product_other_ingredients__other_ingredient'
    ).order_by('-id')  # 전체 제품 표시 (ID 내림차순)

    return render(request, 'products/product_form.html', {
        'ingredients': ingredients,
        "other_ingredients": other_ingredients,
        'small_categories': small_categories,
        'products': products
    })

# Ingredient 입력 화면 (템플릿 기반)
def ingredient_form(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        main_ingredient = request.POST.get('mainIngredient', '').strip()
        min_recommended = request.POST.get('minRecommended', '').strip()
        max_recommended = request.POST.get('maxRecommended', '').strip()

        # JSON 문자열 수신
        effect_raw = request.POST.get('effect', '[]')
        side_raw = request.POST.get('sideEffect', '[]')

        # 문자열 → 리스트 변환
        try:
            effect = json.loads(effect_raw)
        except:
            effect = []

        try:
            side_effect = json.loads(side_raw)
        except:
            side_effect = None

        if not all([name, main_ingredient, min_recommended, max_recommended, effect]):
            messages.error(request, '필수 항목을 모두 입력해주세요.')

        else:
            Ingredient.objects.create(
                name=name,
                mainIngredient=main_ingredient,
                minRecommended=min_recommended,
                maxRecommended=max_recommended,
                effect=effect,
                sideEffect=side_effect or None
            )

            messages.success(request, f'"{name}" 성분이 성공적으로 추가되었습니다.')
            return redirect('admin_ingredient_form')

    ingredients = Ingredient.objects.all().order_by('id')
    return render(request, 'products/ingredient_form.html', {
        'ingredients': ingredients
    })

def ingredient_edit(request, ingredient_id):
    """Ingredient 수정 화면"""
    try:
        ingredient = Ingredient.objects.get(id=ingredient_id)
    except Ingredient.DoesNotExist:
        messages.error(request, '성분을 찾을 수 없습니다.')
        return redirect('admin_ingredient_form')

    if request.method == 'POST':
        ingredient.name = request.POST.get('name', '').strip()
        ingredient.mainIngredient = request.POST.get('mainIngredient', '').strip()
        ingredient.minRecommended = request.POST.get('minRecommended', '').strip()
        ingredient.maxRecommended = request.POST.get('maxRecommended', '').strip()

        effect_raw = request.POST.get('effect', '[]')
        side_raw = request.POST.get('sideEffect', '[]')

        try:
            ingredient.effect = json.loads(effect_raw)
        except:
            ingredient.effect = []

        try:
            ingredient.sideEffect = json.loads(side_raw)
        except:
            ingredient.sideEffect = None

        ingredient.save()

        messages.success(request, f'"{ingredient.name}" 성분이 성공적으로 수정되었습니다.')
        return redirect('admin_ingredient_form')

    return render(request, 'products/ingredient_edit.html', {
        'ingredient': ingredient
    })

# BigCategory 삭제
def big_category_delete(request, category_id):
    """BigCategory 삭제"""
    try:
        category = BigCategory.objects.get(id=category_id)
    except BigCategory.DoesNotExist:
        messages.error(request, '대분류를 찾을 수 없습니다.')
        return redirect('admin_big_category_form')
    
    if request.method == 'POST':
        category_name = category.category
        # 연결된 SmallCategory의 CategoryProduct 먼저 삭제
        small_categories = category.smallCategories.all()
        for small_cat in small_categories:
            CategoryProduct.objects.filter(category=small_cat).delete()
        # BigCategory 삭제 (CASCADE로 SmallCategory도 자동 삭제됨)
        category.delete()
        messages.success(request, f'"{category_name}" 대분류가 성공적으로 삭제되었습니다.')
        return redirect('admin_big_category_form')
    
    return render(request, 'products/big_category_delete_confirm.html', {
        'category': category
    })

# SmallCategory 삭제
def small_category_delete(request, category_id):
    """SmallCategory 삭제"""
    try:
        category = SmallCategory.objects.get(id=category_id)
    except SmallCategory.DoesNotExist:
        messages.error(request, '소분류를 찾을 수 없습니다.')
        return redirect('admin_small_category_form')
    
    if request.method == 'POST':
        category_name = category.category
        # PROTECT된 CategoryProduct 먼저 삭제
        CategoryProduct.objects.filter(category=category).delete()
        # SmallCategory 삭제
        category.delete()
        messages.success(request, f'"{category_name}" 소분류가 성공적으로 삭제되었습니다.')
        return redirect('admin_small_category_form')
    
    return render(request, 'products/small_category_delete_confirm.html', {
        'category': category
    })

# Ingredient 삭제
def ingredient_delete(request, ingredient_id):
    """Ingredient 삭제"""
    try:
        ingredient = Ingredient.objects.get(id=ingredient_id)
    except Ingredient.DoesNotExist:
        messages.error(request, '성분을 찾을 수 없습니다.')
        return redirect('admin_ingredient_form')
    
    if request.method == 'POST':
        ingredient_name = ingredient.name
        # PROTECT된 ProductIngredient 먼저 삭제
        ProductIngredient.objects.filter(ingredient=ingredient).delete()
        # Ingredient 삭제
        ingredient.delete()
        messages.success(request, f'"{ingredient_name}" 성분이 성공적으로 삭제되었습니다.')
        return redirect('admin_ingredient_form')
    
    return render(request, 'products/ingredient_delete_confirm.html', {
        'ingredient': ingredient
    })

# Product 수정 화면 (템플릿 기반)
@transaction.atomic
def product_edit(request, product_id):
    """Product 데이터 수정 화면"""

    try:
        product = Product.objects.prefetch_related(
            'images',
            'ingredients__ingredient',
            'category_products__category__middle_category__big_category',
            'product_other_ingredients__other_ingredient',
            'product_other_ingredients__other_ingredient'
        ).get(id=product_id)
    except Product.DoesNotExist:
        messages.error(request, '제품을 찾을 수 없습니다.')
        return redirect('admin_product_form')

    # ================= 삭제 처리 =================
    if request.method == 'POST' and request.POST.get('action') == 'delete':
        product_name = product.name
        ProductIngredient.objects.filter(product=product).delete()
        CategoryProduct.objects.filter(product=product).delete()
        product.delete()
        messages.success(request, f'"{product_name}" 제품이 성공적으로 삭제되었습니다.')

        return redirect('admin_product_form')

    if request.GET.get('action') == 'delete':
        return render(request, 'products/product_delete_confirm.html', {
            'product': product
        })

    # ================= 수정 처리 =================
    if request.method == 'POST':
        # ---------- 기본 정보 ----------
        product.name = request.POST.get('name', '').strip()
        product.company = request.POST.get('company', '').strip()
        product.productType = request.POST.get('productType', '').strip()
        coupang_raw = request.POST.get('coupang', '').strip()
        product.coupang = coupang_raw or None

        if not all([product.name, product.company, product.productType]):
            messages.error(request, '모든 필수 항목을 입력해주세요.')
            return redirect('admin_product_edit', product_id=product.id)

        product.save()

        # ---------- 이미지 ----------
        delete_image_ids = [
            i for i in request.POST.getlist('delete_image_ids[]') if i.strip()
        ]
        if delete_image_ids:
            ProductImage.objects.filter(id__in=delete_image_ids, product=product).delete()

        new_image_files = request.FILES.getlist('new_image_files')
        if new_image_files:
            uploaded_images = upload_images_to_s3(product, new_image_files)
            ProductImage.objects.bulk_create(uploaded_images)

        # ---------- 성분 삭제 ----------
        delete_ingredient_ids = [
            i for i in request.POST.getlist('delete_ingredient_ids[]') if i.strip()
        ]
        if delete_ingredient_ids:
            ProductIngredient.objects.filter(id__in=delete_ingredient_ids, product=product).delete()

        # ---------- 기존 성분 수정 ----------
        existing_pi_ids = request.POST.getlist('existing_product_ingredient_ids[]')
        existing_ing_ids = request.POST.getlist('existing_ingredient_ids[]')
        existing_amounts = request.POST.getlist('existing_amounts[]')

        for pi_id, ing_id, amount in zip(existing_pi_ids, existing_ing_ids, existing_amounts):
            pi_id = pi_id.strip()
            ing_id = ing_id.strip()
            amount = amount.strip()

            if not (pi_id and ing_id and amount):
                continue

            try:
                pi = ProductIngredient.objects.get(id=pi_id, product=product)
                ingredient = Ingredient.objects.get(id=ing_id)
                pi.ingredient = ingredient
                pi.amount = amount
                pi.save()
            except (ProductIngredient.DoesNotExist, Ingredient.DoesNotExist):
                pass

        # ---------- 새 성분 추가 ----------
        new_ing_ids = request.POST.getlist('new_ingredient_ids[]')
        new_amounts = request.POST.getlist('new_amounts[]')

        for ing_id, amount in zip(new_ing_ids, new_amounts):
            ing_id = ing_id.strip()
            amount = amount.strip()

            if not (ing_id and amount):
                continue

            try:
                ingredient = Ingredient.objects.get(id=ing_id)
                ProductIngredient.objects.create(
                    product=product,
                    ingredient=ingredient,
                    amount=amount
                )
            except Ingredient.DoesNotExist:
                pass

        # ---------- 기존 카테고리 수정 ----------
        existing_cp_ids = request.POST.getlist('existing_category_product_ids[]')
        existing_cat_ids = request.POST.getlist('existing_category_ids[]')

        for cp_id, cat_id in zip(existing_cp_ids, existing_cat_ids):
            cp_id = cp_id.strip()
            cat_id = cat_id.strip()

            if not (cp_id and cat_id):
                continue

            try:
                cp = CategoryProduct.objects.get(id=cp_id, product=product)
                category = SmallCategory.objects.get(id=cat_id)
                cp.category = category
                cp.save()
            except (CategoryProduct.DoesNotExist, SmallCategory.DoesNotExist):
                pass

        # ---------- 기존 카테고리 삭제 ----------
        delete_category_ids = [
            i for i in request.POST.getlist('delete_category_ids[]') if i.strip()
        ]
        if delete_category_ids:
            CategoryProduct.objects.filter(id__in=delete_category_ids, product=product).delete()

        # ---------- 새 카테고리 추가 ----------
        new_category_ids = request.POST.getlist('new_category_ids[]')

        for cat_id in new_category_ids:
            cat_id = cat_id.strip()
            if not cat_id:
                continue

            try:
                category = SmallCategory.objects.get(id=cat_id)
                CategoryProduct.objects.get_or_create(
                    product=product,
                    category=category
                )
            except SmallCategory.DoesNotExist:
                pass

        # 기존 기타 원료 삭제
        delete_ids = request.POST.getlist("delete_other_ingredient_ids[]")
        if delete_ids:
            ProductOtherIngredient.objects.filter(id__in=delete_ids).delete()

        # 기존 기타 원료 수정
        existing_ids = request.POST.getlist("existing_product_other_ingredient_ids[]")
        existing_oi_ids = request.POST.getlist("existing_other_ingredient_ids[]")

        for poi_id, oi_id in zip(existing_ids, existing_oi_ids):
            if oi_id:
                ProductOtherIngredient.objects.filter(id=poi_id).update(
                    other_ingredient_id=oi_id
                )

        # 신규 기타 원료 추가
        new_oi_ids = request.POST.getlist("new_other_ingredient_ids[]")
        for oi_id in new_oi_ids:
            if oi_id:
                ProductOtherIngredient.objects.get_or_create(
                    product=product,
                    other_ingredient_id=oi_id
                )

        messages.success(request, f'"{product.name}" 제품이 성공적으로 수정되었습니다.')
        return redirect('admin_product_form')

    # ================= GET =================
    ingredients = Ingredient.objects.all().order_by('id')
    small_categories = SmallCategory.objects.select_related('middle_category__big_category').all().order_by(
        'middle_category__big_category__id',
        'middle_category__id',
        'id'
    )
    other_ingredients = OtherIngredient.objects.all().order_by("name")

    return render(request, 'products/product_edit.html', {
        'product': product,
        'ingredients': ingredients,
        'other_ingredients': other_ingredients,
        'small_categories': small_categories,
        'action': request.GET.get('action')
    })

# Product 삭제
def product_delete(request, product_id):
    """Product 삭제"""
    
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        messages.error(request, '제품을 찾을 수 없습니다.')
        return redirect('admin_product_form')
    
    if request.method == 'POST':
        product_name = product.name

        # ProductIngredient 삭제
        ProductIngredient.objects.filter(product=product).delete()
        
        # PROTECT로 설정된 CategoryProduct를 먼저 삭제
        CategoryProduct.objects.filter(product=product).delete()
        
        # 이제 제품 삭제 가능
        product.delete()
        messages.success(request, f'"{product_name}" 제품이 성공적으로 삭제되었습니다.')
        return redirect('admin_product_form')
    
    # GET 요청 시 확인 페이지 표시
    return render(request, 'products/product_delete_confirm.html', {
        'product': product
    })

# OtherIngredient 입력 화면 (템플릿 기반)
def other_ingredient_form(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()

        if not name:
            messages.error(request, "기타원료 이름을 입력해주세요.")
        else:
            if OtherIngredient.objects.filter(name=name).exists():
                messages.error(request, "이미 등록된 기타원료입니다.")
            else:
                OtherIngredient.objects.create(name=name)
                messages.success(
                    request,
                    f'"{name}" 기타원료가 성공적으로 추가되었습니다.'
                )
                return redirect("admin_other_ingredient_form")

    other_ingredients = OtherIngredient.objects.all().order_by("id")

    return render(
        request,
        "products/other_ingredient_form.html",
        {
            "other_ingredients": other_ingredients
        }
    )

def other_ingredient_edit(request, pk):
    other = get_object_or_404(OtherIngredient, pk=pk)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()

        if not name:
            messages.error(request, "기타 원료명을 입력해주세요.")
        else:
            other.name = name
            other.save()
            messages.success(request, "기타 원료가 수정되었습니다.")
            return redirect("admin_other_ingredient_form")

    return render(request, "products/other_ingredient_edit.html", {
        "other": other
    })

def other_ingredient_delete(request, pk):
    if request.method != "POST":
        return redirect("admin_other_ingredient_form")

    other = get_object_or_404(OtherIngredient, pk=pk)
    name = other.name
    other.delete()

    messages.success(request, f'"{name}" 기타 원료가 삭제되었습니다.')
    return redirect("admin_other_ingredient_form")

# Product Request 화면 (템플릿 기반)
def product_request_list(request):
    from django.shortcuts import render
    from products.models import ProductRequest

    product_requests = ProductRequest.objects.select_related(
        'user'
    ).order_by('-created_at')

    return render(request, 'products/product_request_list.html', {
        'product_requests': product_requests
    })

def admin_product_request_delete(request, request_id):
    if request.method != "POST":
        messages.error(request, "잘못된 요청입니다.")
        return redirect('admin_product_request_list')

    product_request = get_object_or_404(ProductRequest, id=request_id)
    product_request.delete()

    messages.success(request, "제품 추가 요청이 삭제되었습니다.")
    return redirect('admin_product_request_list')

def ingredient_guide_form(request):
    if request.method == "POST":
        ingredient_id = request.POST.get("ingredient_id")
        key_points_raw = request.POST.get("keyPoints", "[]")
        sources_raw = request.POST.get("sources", "[]")

        try:
            ingredient = Ingredient.objects.get(id=ingredient_id)
        except Ingredient.DoesNotExist:
            messages.error(request, "성분을 찾을 수 없습니다.")
            return redirect("admin_ingredient_guide_form")

        # 이미 가이드 존재하는지 체크
        if IngredientGuide.objects.filter(ingredient=ingredient).exists():
            messages.error(request, "이미 해당 성분의 가이드가 존재합니다.")
            return redirect("admin_ingredient_guide_form")

        try:
            key_points = json.loads(key_points_raw)
        except:
            key_points = []

        try:
            sources = json.loads(sources_raw)
        except:
            sources = []

        IngredientGuide.objects.create(
            ingredient=ingredient,
            keyPoints=key_points,
            sources=sources
        )

        messages.success(request, f'"{ingredient.name}" 가이드가 생성되었습니다.')
        return redirect("admin_ingredient_guide_form")

    ingredients = Ingredient.objects.all().order_by("id")
    guides = IngredientGuide.objects.select_related("ingredient").order_by("-id")

    return render(request, "products/ingredient_guide_form.html", {
        "ingredients": ingredients,
        "guides": guides
    })

def ingredient_guide_edit(request, pk):
    guide = get_object_or_404(IngredientGuide, pk=pk)

    if request.method == "POST":
        key_points_raw = request.POST.get("keyPoints", "[]")
        sources_raw = request.POST.get("sources", "[]")

        try:
            key_points = json.loads(key_points_raw)
        except:
            key_points = []

        try:
            sources = json.loads(sources_raw)
        except:
            sources = []

        guide.keyPoints = key_points
        guide.sources = sources
        guide.save()

        messages.success(request, "가이드가 수정되었습니다.")
        return redirect("admin_ingredient_guide_form")

    return render(
        request,
        "products/ingredient_guide_edit.html",
        {
            "guide": guide
        }
    )

def ingredient_guide_delete(request, guide_id):
    guide = get_object_or_404(IngredientGuide, id=guide_id)

    if request.method == "POST":
        ingredient_name = guide.ingredient.name
        guide.delete()
        messages.success(request, f'"{ingredient_name}" 가이드가 삭제되었습니다.')
        return redirect("admin_ingredient_guide_form")

    return render(request, "products/ingredient_guide_delete_confirm.html", {
        "guide": guide
    })

"""
admin_views.py 맨 아래에 추가할 뷰 함수들

상단 import에 아래 추가 필요:
    from django.http import HttpResponse
    import csv, io, re, time, requests
    import xml.etree.ElementTree as ET
    from rapidfuzz import process, fuzz
    from products.models import ImportJob
"""

import csv
import io
import re
import time
import requests
import xml.etree.ElementTree as ET

from rapidfuzz import process, fuzz
from django.http import HttpResponse


# ------------------------------------------------------------------ #
#  설정값
# ------------------------------------------------------------------ #
API_KEY = settings.FOOD_API_KEY
SERVICE_ID = "I0030"
BASE_URL   = f"https://openapi.foodsafetykorea.go.kr/api/{API_KEY}/{SERVICE_ID}/xml"
BATCH_SIZE = 1000
GARCINIA_KEYWORDS = ["가르시니아"]
FUZZY_THRESHOLD   = 85

STANDARD_INGREDIENTS = [
    "가르시니아캄보지아 추출물", "녹차추출물", "공액리놀레산",
    "키토산", "키토올리고당", "바나바잎추출물", "프로바이오틱스",
    "아연", "비타민A", "비타민B1", "비타민B2", "비타민B6", "비타민B12",
    "비타민C", "비타민D", "비타민E", "비타민K", "나이아신", "판토텐산",
    "비오틴", "엽산", "칼슘", "마그네슘", "철", "구리", "망간",
    "셀레늄", "요오드", "크롬", "몰리브덴", "인", "칼륨",
    "식이섬유", "난소화성말토덱스트린", "알로에겔", "차전자피식이섬유",
    "프락토올리고당", "이눌린", "치커리추출물", "대두이소플라본",
    "코엔자임Q10", "홍삼", "인삼", "밀크시슬추출물", "은행잎추출물",
    "루테인", "글루코사민", "N-아세틸글루코사민", "히알루론산",
    "레시틴", "스쿠알렌", "포스콜린", "카테킨", "코로솔산", "조단백질",
]

EXACT_NAME_MAP = {
    "hydroxycitric acid":               "가르시니아캄보지아 추출물",
    "hydroxycitiric acid":              "가르시니아캄보지아 추출물",
    "hydroxycitiricacid":               "가르시니아캄보지아 추출물",
    "hydroxycitricacid":                "가르시니아캄보지아 추출물",
    "hydroxycitric aicd":               "가르시니아캄보지아 추출물",
    "hca":                              "가르시니아캄보지아 추출물",
    "hca 함량":                         "가르시니아캄보지아 추출물",
    "가르시니아캄보지아추출물":          "가르시니아캄보지아 추출물",
    "가르시니아캄보지아추출물 정":       "가르시니아캄보지아 추출물",
    "-hydroxycitric acid":              "가르시니아캄보지아 추출물",
    "프로바이오틱스 수":                "프로바이오틱스",
    "프로바이오틱스수":                 "프로바이오틱스",
    "아 연":    "아연",
    "망 간":    "망간",
    "셀 렌":    "셀레늄",
    "셀레 늄":  "셀레늄",
    "셀렌":     "셀레늄",
}

INGREDIENT_CATEGORY_MAP = {
    "가르시니아캄보지아 추출물": [1],
    "녹차추출물":               [1],
    "공액리놀레산":             [1],
    "키토산":                  [1],
    "키토올리고당":             [1],
    "바나바잎추출물":           [2],
    "난소화성말토덱스트린":      [2],
    "프로바이오틱스":           [3],
    "알로에겔":                [3],
    "차전자피식이섬유":          [3],
    "프락토올리고당":           [3],
}


# ------------------------------------------------------------------ #
#  정규화 함수
# ------------------------------------------------------------------ #
def _normalize(name: str) -> str:
    return re.sub(r'\s+', '', name).lower()


# ------------------------------------------------------------------ #
#  파싱 유틸
# ------------------------------------------------------------------ #
def _clean_raw_name(raw_name: str) -> str:
    name = raw_name.strip()
    name = re.sub(r'^[\-\s]*[\(\s]*[\d①②③④⑤⑥⑦⑧⑨⑩]+[\)\.\s]+', '', name).strip()
    name = re.sub(r'^[\(\s]*[가나다라마바사아자차카타파하]+[\)\.\s]+', '', name).strip()
    name = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', name).strip()
    name = re.sub(r'^\-\s*', '', name).strip()
    name = re.sub(r'^[총합\s]+', '', name).strip()
    name = re.sub(r'\(-\)-?', '', name).strip()
    name = re.sub(r'\s*[\(\[]\s*[%a-zA-Zμ/g0-9\s]+\s*[\)\]]', '', name).strip()
    name = re.sub(r'\s*(함량|정제|추출물정)\s*$', '', name).strip()
    return name.strip()


def _format_amount(amount_str: str, unit: str) -> str:
    clean = amount_str.replace(",", "").strip()
    try:
        num = int(float(clean))
    except ValueError:
        return f"{amount_str}{unit}"
    if num >= 100_000_000:
        억 = num // 100_000_000
        나머지 = num % 100_000_000
        return f"{억}억{unit}" if 나머지 == 0 else f"{억}억{나머지}{unit}"
    return f"{num}{unit}"


def _match_ingredient(cleaned_name: str, normalized_map: dict) -> tuple:
    exact = EXACT_NAME_MAP.get(cleaned_name.lower().strip())
    if exact:
        return exact, "exact"

    normalized_input = _normalize(cleaned_name)
    result = process.extractOne(
        normalized_input,
        list(normalized_map.keys()),
        scorer=fuzz.token_sort_ratio,
        score_cutoff=FUZZY_THRESHOLD
    )
    if result:
        matched_normalized, score, _ = result
        return normalized_map[matched_normalized], f"fuzzy({score:.0f}%)"

    return cleaned_name, "unmatched"


def _parse_spec(spec_text: str, normalized_map: dict) -> list:
    results = []
    for line in spec_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        match = re.search(
            r'([^:：\n]+?)\s*[:：]\s*표시량[\[(]\s*([0-9,]+(?:\.[0-9]+)?)'
            r'(?:\([^)]*\))?\s*(mg|g|μg|ug|IU|CFU|%)\s*[/]',
            line, re.IGNORECASE
        )
        if not match:
            continue
        raw_name = re.sub(r'^\d+\.\s*', '', match.group(1)).strip()
        cleaned  = _clean_raw_name(raw_name)
        name, method = _match_ingredient(cleaned, normalized_map)
        results.append({
            "raw_name": raw_name,
            "name":     name,
            "amount":   _format_amount(match.group(2), match.group(3)),
            "method":   method,
        })
    return results


def _parse_effect_for_ingredient(effect_text: str, ingredient_name: str) -> list:
    if not effect_text or not ingredient_name:
        return []

    sentences = []
    lines = [l.strip() for l in effect_text.split("\n") if l.strip()]
    ing_normalized = _normalize(ingredient_name)

    for i, line in enumerate(lines):
        if ingredient_name in line or ing_normalized in _normalize(line):
            colon_match = re.search(
                r'(?:\[' + re.escape(ingredient_name) + r'\]|'
                + re.escape(ingredient_name) + r')\s*[:：\]]\s*(.+)',
                line
            )
            if colon_match:
                content = colon_match.group(1).strip()
                parts = re.split(r'\s*[\(\（]\d+[\)\）]\s*|[①②③④⑤⑥]\s*', content)
                sentences.extend([p.strip() for p in parts if p.strip()])
            elif i + 1 < len(lines):
                next_line = lines[i + 1]
                if ":" not in next_line and "：" not in next_line:
                    parts = re.split(r'\s*[\(\（]\d+[\)\）]\s*|[①②③④⑤⑥]\s*', next_line)
                    sentences.extend([p.strip() for p in parts if p.strip()])

    if not sentences and "가르시니아" in ingredient_name:
        for line in lines:
            if "탄수화물이 지방으로 합성" in line:
                content = re.sub(r'^[\(\（]\d+[\)\）]\s*|^[①②③④⑤]\s*', '', line).strip()
                if content:
                    sentences.append(content)

    seen, result = set(), []
    for s in sentences:
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            result.append(s)
    return result


def _fetch_garcinia_data():
    db_names      = list(Ingredient.objects.values_list("name", flat=True))
    candidates    = list(set(db_names + STANDARD_INGREDIENTS))
    normalized_map = {_normalize(name): name for name in candidates}

    products, ingredients, pi_rows, unmatched = [], {}, [], []
    seen_products = set()
    start, total  = 1, None

    while True:
        end  = start + BATCH_SIZE - 1
        resp = requests.get(f"{BASE_URL}/{start}/{end}", timeout=30)
        root = ET.fromstring(resp.content)

        if total is None:
            total_el = root.find("total_count")
            total = int(total_el.text) if total_el is not None else 0

        rows = root.findall("row")
        if not rows:
            break

        for row in rows:
            indiv = row.findtext("INDIV_RAWMTRL_NM") or ""
            if not any(kw in indiv for kw in GARCINIA_KEYWORDS):
                continue

            name    = row.findtext("PRDLST_NM") or ""
            company = row.findtext("BSSH_NM") or ""
            effect  = row.findtext("PRIMARY_FNCLTY") or ""
            spec    = row.findtext("STDR_STND") or ""

            if not name or name in seen_products:
                continue
            seen_products.add(name)

            parsed = _parse_spec(spec, normalized_map) if spec else []
            category_ids = sorted(set(
                cat_id for item in parsed
                for cat_id in INGREDIENT_CATEGORY_MAP.get(item["name"], [])
            )) or [1]

            products.append({
                "name":         name,
                "company":      company,
                "productType":  "건강기능식품",
                "category_ids": ";".join(map(str, category_ids)),
            })

            for item in parsed:
                pi_rows.append({
                    "product_name":    name,
                    "ingredient_name": item["name"],
                    "amount":          item["amount"],
                    "raw_name":        item["raw_name"],
                    "method":          item["method"],
                })
                if item["name"] not in ingredients:
                    effect_list = _parse_effect_for_ingredient(effect, item["name"])
                    ingredients[item["name"]] = "|".join(effect_list)
                if item["method"] == "unmatched":
                    unmatched.append({
                        "raw_name":     item["raw_name"],
                        "cleaned_name": _clean_raw_name(item["raw_name"]),
                    })

        start += BATCH_SIZE
        if start > total:
            break
        time.sleep(1)

    return {
        "products":    products,
        "ingredients": ingredients,
        "pi_rows":     pi_rows,
        "unmatched":   unmatched,
        "total":       len(products),
    }


def _get_job(request):
    """세션의 job_id로 ImportJob 조회. 없으면 None 반환"""
    job_id = request.session.get("import_job_id")
    if not job_id:
        return None
    try:
        from products.models import ImportJob
        return ImportJob.objects.get(id=job_id)
    except Exception:
        return None


def _job_to_data(job) -> dict:
    """ImportJob → 뷰에서 쓰는 data 딕셔너리"""
    return {
        "products":    job.products,
        "ingredients": job.ingredients,
        "pi_rows":     job.pi_rows,
        "unmatched":   job.unmatched,
        "total":       job.total,
    }


def _csv_response(rows, fieldnames, filename):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    response = HttpResponse(
        "\ufeff" + output.getvalue(),
        content_type="text/csv; charset=utf-8"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _read_uploaded_csv(file):
    decoded = file.read().decode("utf-8-sig")
    reader  = csv.DictReader(io.StringIO(decoded))
    return [row for row in reader]


# ------------------------------------------------------------------ #
#  어드민 뷰
# ------------------------------------------------------------------ #
def import_csv_view(request):
    from products.models import ImportJob

    # ── 1. API 수집 → ImportJob 생성 ─────────────────────────────── #
    if request.method == "POST" and request.POST.get("action") == "fetch":
        try:
            data = _fetch_garcinia_data()

            # 기존 job 있으면 삭제
            old_job = _get_job(request)
            if old_job:
                old_job.delete()

            job = ImportJob.objects.create(
                status      = "pending",
                products    = data["products"],
                ingredients = data["ingredients"],
                pi_rows     = data["pi_rows"],
                unmatched   = data["unmatched"],
                total       = data["total"],
            )
            request.session["import_job_id"] = job.id  # ID만 세션에 저장

            messages.success(
                request,
                f"수집 완료 — 제품 {data['total']}개 | "
                f"성분 {len(data['ingredients'])}종 | "
                f"매칭 실패 {len(data['unmatched'])}개"
            )
        except Exception as e:
            messages.error(request, f"수집 실패: {e}")
        return redirect("admin_import_csv")

    # ── 2. CSV 다운로드 ───────────────────────────────────────────── #
    if request.method == "POST" and request.POST.get("action") == "download_csv":
        job = _get_job(request)
        if not job:
            messages.error(request, "먼저 데이터를 수집해주세요.")
            return redirect("admin_import_csv")

        file_type = request.POST.get("file_type", "products")

        if file_type == "products":
            return _csv_response(
                job.products,
                ["name", "company", "productType", "category_ids"],
                "products.csv"
            )
        elif file_type == "ingredients":
            rows = [{"name": k, "effect": v} for k, v in job.ingredients.items()]
            return _csv_response(rows, ["name", "effect"], "ingredients.csv")
        elif file_type == "product_ingredients":
            return _csv_response(
                job.pi_rows,
                ["product_name", "ingredient_name", "amount", "raw_name", "method"],
                "product_ingredients.csv"
            )
        elif file_type == "unmatched":
            return _csv_response(
                job.unmatched,
                ["raw_name", "cleaned_name"],
                "unmatched_ingredients.csv"
            )

    # ── 3. CSV 업로드 → ImportJob 업데이트 ───────────────────────── #
    if request.method == "POST" and request.POST.get("action") == "upload_csv":
        job = _get_job(request)
        if not job:
            messages.error(request, "먼저 데이터를 수집해주세요.")
            return redirect("admin_import_csv")

        upload_type = request.POST.get("upload_type")
        file        = request.FILES.get("csv_file")

        if not file:
            messages.error(request, "CSV 파일을 선택해주세요.")
            return redirect("admin_import_csv")

        try:
            rows = _read_uploaded_csv(file)

            if upload_type == "products":
                job.products = rows
                job.total    = len(rows)
                messages.success(request, f"products.csv 업로드 완료 — {len(rows)}개 제품")
            elif upload_type == "ingredients":
                job.ingredients = {r["name"]: r.get("effect", "") for r in rows}
                messages.success(request, f"ingredients.csv 업로드 완료 — {len(rows)}개 성분")
            elif upload_type == "product_ingredients":
                job.pi_rows = rows
                messages.success(request, f"product_ingredients.csv 업로드 완료 — {len(rows)}개 연결")

            job.save()

        except Exception as e:
            messages.error(request, f"CSV 파싱 실패: {e}")

        return redirect("admin_import_csv")

    # ── 4. DB 저장 ────────────────────────────────────────────────── #
    if request.method == "POST" and request.POST.get("action") == "import":
        job = _get_job(request)
        if not job:
            messages.error(request, "먼저 데이터를 수집하거나 CSV를 업로드해주세요.")
            return redirect("admin_import_csv")

        ing_created = ing_updated = 0
        prod_created = prod_updated = cat_created = pi_created = pi_updated = pi_fail = 0

        # Ingredients — name 기준 update_or_create
        for name, effect_str in job.ingredients.items():
            effect_list = [e.strip() for e in effect_str.split("|") if e.strip()]
            defaults = {"effect": effect_list, "sideEffect": []}
            if name == "가르시니아캄보지아 추출물":
                defaults.update({
                    "mainIngredient": "Hydroxycitric acid (HCA)",
                    "minRecommended": "750mg",
                    "maxRecommended": "2800mg",
                })
            _, created = Ingredient.objects.update_or_create(
                name=name, defaults=defaults
            )
            if created:
                ing_created += 1
            else:
                ing_updated += 1

        # Products + CategoryProduct — name 기준 update_or_create
        for row in job.products:
            product, created = Product.objects.update_or_create(
                name=row["name"],
                defaults={
                    "company":     row.get("company", ""),
                    "productType": row.get("productType", "건강기능식품"),
                }
            )
            if created:
                prod_created += 1
            else:
                prod_updated += 1

            for cat_id in [
                int(c) for c in row.get("category_ids", "1").split(";")
                if c.strip().isdigit()
            ]:
                try:
                    category = SmallCategory.objects.get(id=cat_id)
                    _, cc = CategoryProduct.objects.get_or_create(
                        product=product, category=category
                    )
                    if cc:
                        cat_created += 1
                except SmallCategory.DoesNotExist:
                    pass

        # ProductIngredients — product+ingredient 기준 update_or_create
        for row in job.pi_rows:
            try:
                product    = Product.objects.get(name=row["product_name"])
                ingredient = Ingredient.objects.get(name=row["ingredient_name"])
                _, created = ProductIngredient.objects.update_or_create(
                    product=product,
                    ingredient=ingredient,
                    defaults={"amount": row.get("amount", "")}
                )
                if created:
                    pi_created += 1
                else:
                    pi_updated += 1
            except (Product.DoesNotExist, Ingredient.DoesNotExist):
                pi_fail += 1

        # Job 완료 처리
        job.status = "done"
        job.products = []
        job.ingredients = {}
        job.pi_rows = []
        job.unmatched = []
        job.save()
        del request.session["import_job_id"]

        messages.success(
            request,
            f"DB 저장 완료 — "
            f"Ingredient 생성: {ing_created} / 수정: {ing_updated} | "
            f"Product 생성: {prod_created} / 수정: {prod_updated} | "
            f"카테고리 연결: {cat_created} | "
            f"성분 연결 생성: {pi_created} / 수정: {pi_updated} (실패: {pi_fail})"
        )
        return redirect("admin_import_csv")

    # ── GET ───────────────────────────────────────────────────────── #
    job  = _get_job(request)
    data = _job_to_data(job) if job else None
    return render(request, "products/import_csv.html", {"data": data})