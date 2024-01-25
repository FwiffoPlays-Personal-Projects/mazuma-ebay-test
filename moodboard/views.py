from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from zipfile import ZipFile
from datetime import datetime, time
from io import BytesIO
from PIL import Image as PILImage
from PIL import ImageEnhance
from pyzbar.pyzbar import decode as qr_decode
import base64
import pytesseract
import requests
import numpy as np
import os
import json
import re
import cv2
import time

from .forms import MoodboardForm, ImageForm
from .models import Moodboard, Image

if os.path.isfile('env.py'):
    import env

if 'DEBUG' in os.environ:
    DEBUG = True
    print("DEBUG MODE ENABLED")
else:
    DEBUG = False

def create_moodboard(request):
    """
    Handles the creation of a new Moodboard.

    If the request method is POST, this function validates the submitted form,
    uploads images to Cloudinary, and creates a Moodboard object.
    If the request method is GET, this function renders a form to create a new
    Moodboard.
    """
    if request.method == "POST":
        form = MoodboardForm(request.POST)

        if form.is_valid():
            if request.FILES.getlist("image"):
                moodboard = form.save(commit=False)
                # Don't save the instance yet
                moodboard.user = (
                    request.user
                )  # Associate the logged-in user with the moodboard
                moodboard = form.save()  # Save the moodboard instance

                for img in request.FILES.getlist("image"):
                    new_image = Image(image=img, moodboard=moodboard)
                    new_image.save()
                    #Image.objects.create(moodboard=moodboard, image=image_url)
                return redirect("moodboard:index")
            else:
                # Display an error to the user if no images are uploaded
                messages.error(request, "Please upload at least one image")
    else:
        form = MoodboardForm()

    context = {
        "form": form,
        # 'image_form': image_form,
    }

    return render(request, "moodboard/create_moodboard.html", context)


@login_required
def edit_moodboard(request, moodboard_id):
    """
    Handles the editing of an existing Moodboard.

    If the user has permission to edit the Moodboard, this function allows
    them to modify the Moodboard's title, description, tags, and images.
    If the user does not have permission, a 403 Forbidden response is returned.
    """
    moodboard = get_object_or_404(Moodboard, pk=moodboard_id)

    if request.user == moodboard.user or request.user.is_staff:
        if request.method == "POST":
            form = MoodboardForm(request.POST, instance=moodboard)
            if form.is_valid():
                form.save()

                if request.FILES.getlist("image"):
                    # Delete existing images
                    Image.objects.filter(moodboard=moodboard).delete()

                    # Upload new images
                    for img in request.FILES.getlist("image"):
                        # Upload new images
                        Image.objects.create(moodboard=moodboard, image=img)

                messages.success(request, "Item has been updated.")
                return redirect("moodboard:detail", pk=moodboard_id)
        else:
            form = MoodboardForm(instance=moodboard)
        images = Image.objects.filter(moodboard=moodboard)
        return render(
            request,
            "moodboard/edit_moodboard.html",
            {"form": form, "images": images, "moodboard": moodboard},
        )
    else:
        return HttpResponseForbidden(
            "You don't have permission to edit this Item."
        )


@login_required
def delete_moodboard(request, pk):
    """
    Handles the deletion of a Moodboard.

    If the user has permission to delete the Moodboard, it is deleted and the
    user is redirected to the index page. If the user does not have
    permission, an error message is displayed.
    """
    moodboard = get_object_or_404(Moodboard, pk=pk)

    if request.user == moodboard.user or request.user.is_staff:
        moodboard.delete()
        messages.success(request, "Item has been deleted.")
        return redirect("moodboard:index")
    else:
        messages.error(request, "You do not have permission to delete this "
                                "item.")
        return redirect("moodboard:detail", pk=pk)


def get_queryset(request):
    """
    Returns a queryset of Moodboard objects based on the search query.

    If there is a search query, this function filters Moodboard objects by
    title, description, or tags containing the query. If there is no
    search query, it returns all Moodboard objects.
    """
    query = request.GET.get("q")
    if query:
        moodboards = Moodboard.objects.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__icontains=query)
            | Q(manufacturer__icontains=query)
            | Q(model_number__icontains=query)
            | Q(stock_id__icontains=query)
            | Q(listed__icontains=query)
        )
    else:
        moodboards = Moodboard.objects.all()
    return moodboards


def index(request):
    """
    Displays a list of all Moodboard objects or a filtered list based on the
    search query.
    """
    moodboards_list = get_queryset(request)
    
    listed_option = request.GET.get('listed_option')

    if listed_option == 'True':
        moodboards_list = moodboards_list.filter(listed=True)
    elif listed_option == 'False':
        moodboards_list = moodboards_list.filter(listed=False)

    # Retrieve date range from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        print("DEBUG: Start date = ", start_date)
        start_date_naive = datetime.strptime(start_date, '%Y-%m-%d').date()
        # Combine date with the start of the day (midnight) and make it timezone-aware
        # start_date_aware = timezone.make_aware(datetime.combine(start_date_naive, time.min))
        print(str(moodboards_list.filter(listed_at__gte=start_date_naive)))
        moodboards_filtered = moodboards_list.filter(listed_at__gte=start_date_naive)
    else:
        moodboards_filtered = moodboards_list
        
    #if end_date:
     #   print("DEBUG: End date = ", end_date)
     #   end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
     #   moodboards_filtered = moodboards_list.filter(listed_at__lte=end_date)

    paginator = Paginator(moodboards_filtered, 10)  # Show 10 items per page

    page = request.GET.get('page')

    try:
        moodboards_result = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        moodboards_result = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        moodboards_result = paginator.page(paginator.num_pages)

    context = {
        "moodboards": moodboards_result,
        "listed_option": listed_option,
        "start_date": start_date,
        "end_date": end_date,
    }

    return render(request, "moodboard/index.html", context)


def detail(request, pk):
    """
    Displays the details of a Moodboard, including its title, description,
    tags, and images.
    """
    moodboard = Moodboard.objects.get(pk=pk)
    images = Image.objects.filter(moodboard_id=pk)
    context = {"moodboard": moodboard, "images": images}
    return render(request, "moodboard/detail.html", context)


def download_all_images(request, moodboard_id):
    moodboard = Moodboard.objects.get(pk=moodboard_id)
    images = moodboard.images.all()

    # Initialize a BytesIO object to store the zip file
    zip_buffer = BytesIO()

    # Get current timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    with ZipFile(zip_buffer, 'w') as zip_file:
        for image in images:
            # Read each image directly from the local storage
            img_data = image.image.read()  # Assuming 'image' is the FileField in your Image model
            img_buffer = BytesIO(img_data)

            # Important: Reset the buffer pointer to the beginning
            img_buffer.seek(0)

            # Add the image to the zip file
            zip_file.writestr(f"{image.id}.jpg", img_buffer.read())

    # Prepare the zip file for download
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename={moodboard.title}_{timestamp}.zip'

    return response


def toggle_listed(request, moodboard_id):
    moodboard = get_object_or_404(Moodboard, pk=moodboard_id)

    if request.user == moodboard.user or request.user.is_staff:
        moodboard.listed = not moodboard.listed

                # If toggled to true, update the listed_date
        if moodboard.listed:
            moodboard.listed_at = datetime.now()
            moodboard.listed_by = request.user.username

        moodboard.save()
        return redirect('moodboard:detail', pk=moodboard.id)
    else:
        return JsonResponse({'error': 'Unauthorized'}, status=401)


def set_stock_id(request, moodboard_id, stock_id):
    moodboard = get_object_or_404(Moodboard, pk=moodboard_id)

    if request.user == moodboard.user or request.user.is_staff:
        moodboard.stock_id = stock_id

        moodboard.save()
        return JsonResponse({'stock_id': stock_id}, status=200)
    else:
        return JsonResponse({'error': 'Unauthorized'}, status=401)


@csrf_exempt
def set_description(request, moodboard_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        moodboard = get_object_or_404(Moodboard, pk=moodboard_id)
        description = data.get('description', '')

        moodboard.description = description
        moodboard.save()

        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)


def pil_to_cv2(image):
    """Convert PIL Image to OpenCV Image."""
    return np.array(image)


def cv2_to_pil(image):
    """Convert OpenCV Image to PIL Image."""
    return Image.fromarray(image)


def extract_qr_data(pil_image, padding=25):
    """Extracts QR code data from an image, visualizes the codes, and returns the data."""
    # Load the image with OpenCV
    image = pil_to_cv2(pil_image)
    
    # Detect and decode QR codes
    detected_qr_codes = qr_decode(pil_image)
    qr_data_list = []

    for qr_code in detected_qr_codes:
        points = qr_code.polygon
        
        if len(points) == 4:
            # Convert polygon points to x and y coordinates
            x_coords = [point.x for point in points]
            y_coords = [point.y for point in points]
            
            # Calculate bounding box with padding for cropping and visualization
            top_left = (max(min(x_coords) - padding, 0), max(min(y_coords) - padding, 0))
            bottom_right = (min(max(x_coords) + padding, image.shape[1]), min(max(y_coords) + padding, image.shape[0]))
            
            # Visualize the bounding box on the image
            cv2.rectangle(image, top_left, bottom_right, (0, 255, 0), 2)
            
            # Crop and decode QR code data
            cropped_image = image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
            decoded_data = decode_qr_from_cv2(cropped_image)
            if decoded_data:
                qr_data_list.append(decoded_data)

    # Write the visualized image to disk only if there are detected QR codes
    if detected_qr_codes:
        output_path = os.path.join(settings.MEDIA_ROOT, "testing", "main_image.jpg")
        cv2.imwrite(output_path, image)
        # print(f"DEBUG: Main image with visualized QR codes saved to: {output_path}")
    
    return qr_data_list


def decode_qr_from_cv2(cv2_image):
    pil_image = PILImage.fromarray(cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB))
    decoded_objects = qr_decode(pil_image)
    if decoded_objects:
        return decoded_objects[0].data.decode('utf-8')
    else:
        return None


def base64_to_image(base64_string):
    img_data = base64.b64decode(base64_string)
    return PILImage.open(BytesIO(img_data))


def preprocess_image(pil_img):

    # Convert the image to grayscale to improve contrast for OCR
    grayscale_image = pil_img.convert("L")

    # Increase the contrast of the image
    
    contrast_enhancer = ImageEnhance.Contrast(grayscale_image)
    enhanced_image = contrast_enhancer.enhance(2)

    return enhanced_image

@csrf_exempt
def extract_text(request):
    start_time = time.time()  # Start time measurement
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            base64_string = data.get('image')
            if not base64_string:
                if DEBUG:
                    print("DEBUG: No image data provided.")
                return HttpResponseBadRequest("No image data provided.")
            
            pil_img = base64_to_image(base64_string)
            enhanced_image = preprocess_image(pil_img)
            #cv2_img = pil_to_cv2(pil_img)

            # Convert image to grayscale
            #gray_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)

            # Apply thresholding
            #_, thresh_img = cv2.threshold(gray_img, 0, 200, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Apply adaptive thresholding
            #adaptive_thresh_img = cv2.adaptiveThreshold(gray_img, 240, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            #                            cv2.THRESH_BINARY, 9, 1)

            # Remove noise
            #filtered_img = cv2.medianBlur(gray_img, 3)

            # Apply dilation and erosion to merge text into meaningful lines/words.
            #kernel = np.ones((5,5),np.uint8)
            #img_dilation = cv2.dilate(filtered_img, kernel, iterations=1)
            #img_erosion = cv2.erode(img_dilation, kernel, iterations=1)

            # Save the preprocessed image (for testing purposes)
            output_path = os.path.join(settings.MEDIA_ROOT, "testing", "preprocessed_text_image.jpg")
            cv2.imwrite(output_path, pil_to_cv2(enhanced_image))

            extracted_text = pytesseract.image_to_string(
                enhanced_image,
                lang='eng',
                config='--oem 1'
            )
            
            if not extracted_text:
                if DEBUG:
                    print("DEBUG: No text found.")
                return JsonResponse({"error": "No text found."}, status=400)
            else:
                if DEBUG:
                    end_time = time.time()  # End time measurement
                    duration = end_time - start_time  # Calculate the duration
                    print("DEBUG: Extracted Text: \n", extracted_text)
                    print(f"DEBUG: extract_text took {duration} seconds.")
                return JsonResponse({'extracted_text': extracted_text})

        except json.JSONDecodeError as e:
            if DEBUG:
                print("DEBUG: Invalid JSON data.")
            return HttpResponseBadRequest("Invalid JSON data.")
        except Exception as e:
            print(str(e))
            return HttpResponseBadRequest(str(e))
    else:
        if DEBUG:
            print("DEBUG: Invalid request method.")
        return HttpResponseBadRequest("Invalid request method.")


@csrf_exempt
def extract_stock_id(request):
    start_time = time.time()  # Start time measurement
    pattern = r'MAZ\d{10}'
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            base64_string = data.get('image')
            if not base64_string:
                if DEBUG:
                    print("DEBUG: No image data provided.")
                return HttpResponseBadRequest("No image data provided.")

            
            pil_img = base64_to_image(base64_string)
            enhanced_image = preprocess_image(pil_img)
            qr_data = extract_qr_data(enhanced_image)
            
            if not qr_data:  # No QR data extracted
                if DEBUG:
                    print("DEBUG: No QR data found.")
                return JsonResponse({"error": "No QR data found."}, status=400)
            else:
                if DEBUG:
                    print("DEBUG: Extracted QR Data: ", qr_data)  # Add this to check the QR data

            qr_data_str = ', '.join(filter(None, qr_data))
            match = re.search(pattern, qr_data_str)
            if match:
                stock_id = match.group(0)
                if DEBUG:
                    end_time = time.time()  # End time measurement
                    duration = end_time - start_time  # Calculate the duration
                    print("DEBUG: Found Stock ID: ", stock_id)
                    print(f"DEBUG: extract_stock_id took {duration} seconds.")
                return JsonResponse({'stock_id': stock_id})
            else:
                
                print("ERROR: No Stock ID Found in QR Data: ", qr_data_str)  # Add the QR data here for debugging
                return JsonResponse({"error": "No Stock ID found in QR data."}, status=400)
        except json.JSONDecodeError as e:
            if DEBUG:
                print("DEBUG: Invalid JSON data.")
            return HttpResponseBadRequest("Invalid JSON data.")
        except Exception as e:
            print(str(e))
            return HttpResponseBadRequest(str(e))
    else:
        if DEBUG:
            print("DEBUG: Invalid request method.")
        return HttpResponseBadRequest("Invalid request method.")
