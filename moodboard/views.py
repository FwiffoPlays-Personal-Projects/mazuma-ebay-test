from django.shortcuts import render, redirect, get_object_or_404
#import cloudinary.uploader
from django.db.models import Q
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from zipfile import ZipFile
from datetime import datetime
from io import BytesIO
from PIL import Image as PILImage
from pyzbar.pyzbar import decode as qr_decode
import pytesseract
import requests
import numpy as np
import os
import cv2

from .forms import MoodboardForm, ImageForm
from .models import Moodboard, Image


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
    moodboards = get_queryset(request)
    return render(request, "moodboard/index.html", {"moodboards": moodboards})


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

        moodboard.save()
        return redirect('moodboard:detail', pk=moodboard.id)
    else:
        return JsonResponse({'error': 'Unauthorized'}, status=401)


def listed_items(request):
    moodboards = Moodboard.objects.filter(listed=True)
    return render(request, "moodboard/index.html", {"moodboards": moodboards})


def not_listed_items(request):
    moodboards = Moodboard.objects.filter(listed=False)
    return render(request, "moodboard/index.html", {"moodboards": moodboards})

def locate_qr_codes(image_path):
    image = PILImage.open(image_path)
    decoded_objects = decode(image)

    qr_locations = []
    for obj in decoded_objects:
        if obj.type == "QRCODE":
            qr_locations.append(obj.polygon)  # polygon gives the four corners of the QR code

    return qr_locations, decoded_objects

def visualise_qr_codes(image_path):
    image = cv2.imread(image_path)

    # Decode the QR codes in the image
    detected_qr_codes = qr_decode(image)

    for qr_code in detected_qr_codes:
        points = qr_code.polygon

        # Extract x and y coordinates from the points
        x_coords = [point.x for point in points]
        y_coords = [point.y for point in points]

        # Determine corners of the bounding box
        top_left = (max(0, min(x_coords) - 50), max(0, min(y_coords) - 50))
        bottom_right = (min(image.shape[1], max(x_coords) + 50), min(image.shape[0], max(y_coords) + 50))

        cv2.rectangle(image, top_left, bottom_right, (0, 255, 0), 2)

    # Construct the output path using the directory of the input image
    directory = os.path.dirname(image_path)
    output_path = os.path.join(directory, "testing/qr_visual.jpg")

    cv2.imwrite(output_path, image)
    print("DEBUG: QR Visualisation saved to: "+output_path)



def extract_qr_data(image_path, padding=25):
    # Load the image with OpenCV
    image = cv2.imread(image_path)
    output_path = os.path.join(os.path.dirname(image_path), "testing/main_image.jpg")
    
    # Visualize detected QR codes
    detected_qr_codes = qr_decode(image)
    for qr_code in detected_qr_codes:
        points = qr_code.polygon
        if len(points) == 4:
            x_coords = [point.x for point in points]
            y_coords = [point.y for point in points]
            
            # Adjust bounding box with padding for visualization
            top_left_vis = (max(min(x_coords) - padding, 0), max(min(y_coords) - padding, 0))
            bottom_right_vis = (min(max(x_coords) + padding, image.shape[1]), min(max(y_coords) + padding, image.shape[0]))
            
            cv2.rectangle(image, top_left_vis, bottom_right_vis, (0, 255, 0), 2)
    
    cv2.imwrite(output_path, image)
    print(f"DEBUG: Main image with visualized QR codes saved to: {output_path}")

    # Crop the detected QR codes and decode
    qr_data_list = []
    for qr_code in detected_qr_codes:
        points = qr_code.polygon
        
        x_coords = [point.x for point in points]
        y_coords = [point.y for point in points]
        
        # Get bounding box with padding for cropping
        top_left_crop = (max(min(x_coords) - padding, 0), max(min(y_coords) - padding, 0))
        bottom_right_crop = (min(max(x_coords) + padding, image.shape[1]), min(max(y_coords) + padding, image.shape[0]))
        
        cropped_image = image[top_left_crop[1]:bottom_right_crop[1], top_left_crop[0]:bottom_right_crop[0]]
        qr_data_list.append(decode_qr_from_cv2(cropped_image))
    
    return qr_data_list

def decode_qr_from_cv2(cv2_image):
    pil_image = PILImage.fromarray(cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB))
    decoded_objects = qr_decode(pil_image)
    if decoded_objects:
        return decoded_objects[0].data.decode('utf-8')
    else:
        return None

def extract_text(request, image_id):
    if request.method == 'POST':
        try:
            image_instance = Image.objects.get(id=image_id)
            image_path = image_instance.image.path  # Replace `image` with your image field name
            image = PILImage.open(image_path)
            extracted_text = pytesseract.image_to_string(image)

            qr_data = extract_qr_data(image_path)

            if qr_data:
                extracted_text += "\n QR Data: " + ', '.join(map(str, qr_data))

            return JsonResponse({'extracted_text': extracted_text}, status=200)
        except Image.DoesNotExist:
            return JsonResponse({'error': 'Image not found'}, status=404)