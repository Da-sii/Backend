# 관리자용 템플릿 뷰
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count
from products.models import Product, BigCategory, SmallCategory, ProductIngredient, ProductImage, Ingredient, CategoryProduct, OtherIngredient, ProductOtherIngredient
from products.utils import upload_images_to_s3
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

# SmallCategory 입력 화면 (템플릿 기반)
def small_category_form(request):
    """SmallCategory 데이터 입력 화면"""
    
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
                return redirect('admin_small_category_form')
            except BigCategory.DoesNotExist:
                messages.error(request, '선택한 대분류를 찾을 수 없습니다.')
    
    # 기존 데이터 가져오기
    big_categories = BigCategory.objects.all().order_by('id')
    small_categories = SmallCategory.objects.select_related('bigCategory').all().order_by('bigCategory__id', 'id')
    
    return render(request, 'products/small_category_form.html', {
        'big_categories': big_categories,
        'small_categories': small_categories
    })

def small_category_edit(request, category_id):
    """SmallCategory 수정 화면"""
    try:
        small_category = SmallCategory.objects.get(id=category_id)
    except SmallCategory.DoesNotExist:
        messages.error(request, '소분류를 찾을 수 없습니다.')
        return redirect('admin_small_category_form')

    if request.method == 'POST':
        big_category_id = request.POST.get('bigCategory', '').strip()
        category_name = request.POST.get('category', '').strip()
        
        if not big_category_id:
            messages.error(request, '대분류를 선택해주세요.')
        elif not category_name:
            messages.error(request, '소분류 이름을 입력해주세요.')
        else:
            try:
                big_category = BigCategory.objects.get(id=big_category_id)
                small_category.bigCategory = big_category
                small_category.category = category_name
                small_category.save()
                messages.success(request, f'"{big_category.category} - {category_name}" 소분류가 성공적으로 수정되었습니다.')
                return redirect('admin_small_category_form')
            except BigCategory.DoesNotExist:
                messages.error(request, '선택한 대분류를 찾을 수 없습니다.')

    big_categories = BigCategory.objects.all().order_by('id')
    
    return render(request, 'products/small_category_edit.html', {
        'small_category': small_category,
        'big_categories': big_categories
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
    small_categories = SmallCategory.objects.select_related('bigCategory').all().order_by('bigCategory__id', 'id')
    other_ingredients = OtherIngredient.objects.all().order_by("name")

    # 제품 정보를 더 자세히 가져오기 (이미지, 성분, 카테고리 개수 포함)
    products = Product.objects.annotate(
        image_count=Count('images', distinct=True),
        ingredient_count=Count('ingredients', distinct=True),
        category_count=Count('category_products', distinct=True)
    ).prefetch_related(
        'images',
        'ingredients',
        'category_products__category__bigCategory',
        'product_other_ingredients__other_ingredient'
    ).order_by('id')  # 전체 제품 표시 (ID 오름차순)

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
            'category_products__category__bigCategory',
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
    small_categories = SmallCategory.objects.select_related('bigCategory').all().order_by('bigCategory__id', 'id')
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