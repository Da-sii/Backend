# 관리자용 템플릿 뷰
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count
from products.models import Product, BigCategory, SmallCategory, ProductIngredient, ProductImage, Ingredient, CategoryProduct

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
def product_form(request):
    """Product 데이터 입력 화면"""
    
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
                return redirect('admin_product_form')
            except ValueError:
                messages.error(request, '가격은 숫자로 입력해주세요.')
            except Exception as e:
                messages.error(request, f'오류가 발생했습니다: {str(e)}')
    
    # 기존 데이터 가져오기
    ingredients = Ingredient.objects.all().order_by('name')
    small_categories = SmallCategory.objects.select_related('bigCategory').all().order_by('bigCategory__id', 'id')
    # 제품 정보를 더 자세히 가져오기 (이미지, 성분, 카테고리 개수 포함)
    products = Product.objects.annotate(
        image_count=Count('images', distinct=True),
        ingredient_count=Count('ingredients', distinct=True),
        category_count=Count('category_products', distinct=True)
    ).prefetch_related(
        'images',
        'ingredients',
        'category_products__category__bigCategory'
    ).order_by('-id')  # 전체 제품 표시
    
    return render(request, 'products/product_form.html', {
        'ingredients': ingredients,
        'small_categories': small_categories,
        'products': products
    })

# Ingredient 입력 화면 (템플릿 기반)
def ingredient_form(request):
    """Ingredient 데이터 입력 화면"""
    
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
            return redirect('admin_ingredient_form')
    
    # 기존 성분 목록 가져오기
    ingredients = Ingredient.objects.all().order_by('name')
    
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
        name = request.POST.get('name', '').strip()
        english_ingredient = request.POST.get('englishIngredient', '').strip()
        min_recommended = request.POST.get('minRecommended', '').strip()
        max_recommended = request.POST.get('maxRecommended', '').strip()
        effect = request.POST.get('effect', '').strip()
        side_effect = request.POST.get('sideEffect', '').strip()

        if not all([name, english_ingredient, min_recommended, max_recommended, effect]):
            messages.error(request, '필수 항목을 모두 입력해주세요.')
        else:
            ingredient.name = name
            ingredient.englishIngredient = english_ingredient
            ingredient.minRecommended = min_recommended
            ingredient.maxRecommended = max_recommended
            ingredient.effect = effect
            ingredient.sideEffect = side_effect if side_effect else None
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
def product_edit(request, product_id):
    """Product 데이터 수정 화면"""
    
    try:
        product = Product.objects.prefetch_related(
            'images',
            'ingredients__ingredient',
            'category_products__category__bigCategory'
        ).get(id=product_id)
    except Product.DoesNotExist:
        messages.error(request, '제품을 찾을 수 없습니다.')
        return redirect('admin_product_form')
    
    # 삭제 처리
    if request.method == 'POST' and request.POST.get('action') == 'delete':
        product_name = product.name
        CategoryProduct.objects.filter(product=product).delete()
        product.delete()
        messages.success(request, f'"{product_name}" 제품이 성공적으로 삭제되었습니다.')
        return redirect('admin_product_form')
    
    # 삭제 확인 페이지
    if request.GET.get('action') == 'delete':
        return render(request, 'products/product_delete_confirm.html', {
            'product': product
        })
    
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
            return redirect('admin_product_edit', product_id=product_id)
        
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
            return redirect('admin_product_form')
    
    # 기존 데이터 가져오기
    ingredients = Ingredient.objects.all().order_by('name')
    small_categories = SmallCategory.objects.select_related('bigCategory').all().order_by('bigCategory__id', 'id')
    
    return render(request, 'products/product_edit.html', {
        'product': product,
        'ingredients': ingredients,
        'small_categories': small_categories
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

