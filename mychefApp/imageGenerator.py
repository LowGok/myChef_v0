from google import genai
import os
import cloudinary
import cloudinary.uploader
import streamlit as st
import requests
from urllib.parse import quote

def imageGenerator(meal, ingredient_list):
    client = genai.Client(api_key=st.secrets["gemini_api_key"])

    result = client.models.generate_images(
        model="models/imagen-4.0-generate-001",
        prompt=f"""
                Prompt Type: Image Generation
                AI Model: Optimized for photographic realism and food styling.
                Goal: Generate an appetizing and visually appealing image.
                Subject: Centered, top-view, family-style portion of {meal} showcasing {ingredient_list}, filling a significant portion of the frame. The dish is presented on a white marble surface.
                Style: Clean, bright, fresh, high-quality, and approachable.
                Lighting: Natural or studio-like.
                Perspective: Top-down.
                Negative Prompt: Avoid harsh shadows, clutter, artificial colors, and blurry focus. No cutlery or kitchen cooking tools. No text or other elements on the image.""",
        config=dict(
            number_of_images=1,
            output_mime_type="image/jpeg",
            person_generation="ALLOW_ADULT",
            aspect_ratio="4:3",
        ),
    )
    if not result.generated_images:
        print("No images generated.")
        return False
    generated_image_data = result.generated_images[0].image.image_bytes
    return generated_image_data

def uploadImageToCloud(image_data, public_id_prefix="mychef_meal_img_"):
    try:
        # Cloudinary will automatically assign a unique public_id if not specified.
        # We can pass a prefix to make it more organized.
        response = cloudinary.uploader.upload(image_data, folder="my_generated_images",
                                             resource_type="image",
                                             public_id=f"{public_id_prefix}{os.urandom(4).hex()}") # Simple unique ID
        if response and "secure_url" in response:
            print(f"   Uploaded to Cloudinary successfully. Public ID: {response.get('public_id')}")
            return response
        else:
            print(f"   Cloudinary upload failed or missing secure_url: {response}")
            return None
    except cloudinary.exceptions.Error as e:
        print(f"Error uploading to Cloudinary: {e}")
        st.error("Error uploading images. Please contact admin@gkldevelopment.com")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during Cloudinary upload: {e}")
        st.error("Error uploading images. Please contact admin@gkldevelopment.com")
        return None