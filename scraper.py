def process_product_data(product):
    # Calculate additional metrics
    avg_price = float(product.get('price', 0))
    available_ratio = 1 if product.get('available', False) else 0
    num_images = len(product.get('all_image_srcs', '').split(',')) if product.get('all_image_srcs') else 0
    num_tags = len(product.get('tags', '').split(',')) if product.get('tags') else 0
    description_length = len(product.get('body_html', '')) if product.get('body_html') else 0

    return {
        **product,
        'avg_price': avg_price,
        'available_ratio': available_ratio,
        'num_images': num_images,
        'num_tags': num_tags,
        'description_length': description_length
    } 