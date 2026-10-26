from google import genai
import os
import cloudinary
import cloudinary.uploader
import streamlit as st

def imageGenerator(meal, ingredient_list):
    """Generate image bytes using the supported Gemini content API."""
    from connection import genai_http_options
    client = genai.Client(api_key=st.secrets["gemini_api_key"],
                          http_options=genai_http_options())
    model = os.environ.get("MYCHEF_IMAGE_MODEL") or st.secrets.get("gemini_image_model", "gemini-3.1-flash-image")
    result = client.models.generate_content(
        model=model,
        contents=f"""Generate a realistic food photograph of {meal}, made with {ingredient_list}.
        Show a family-style portion centered on a white marble surface from above.
        Use natural light. Include no text, cutlery or kitchen tools.""",
        config={"response_modalities": ["IMAGE", "TEXT"]},
    )
    for candidate in result.candidates or []:
        if candidate.content is None:
            continue
        for part in candidate.content.parts or []:
            if part.inline_data is not None and part.inline_data.data:
                return part.inline_data.data
    return False

def uploadImageToCloud(image_data, public_id_prefix="mychef_meal_img_"):
    try:
        # Cloudinary will automatically assign a unique public_id if not specified.
        # We can pass a prefix to make it more organized.
        response = cloudinary.uploader.upload(image_data, folder="my_generated_images",
                                             resource_type="image",
                                             timeout=30,
                                             public_id=f"{public_id_prefix}{os.urandom(4).hex()}") # Simple unique ID
        if response and "secure_url" in response:
            print(f"   Uploaded to Cloudinary successfully. Public ID: {response.get('public_id')}")
            return response
        else:
            print(f"   Cloudinary upload failed or missing secure_url: {response}")
            return None
    except cloudinary.exceptions.Error as e:
        print(f"Error uploading to Cloudinary: {e}")
        st.warning("The image could not be uploaded. Your saved recipe will use a placeholder.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during Cloudinary upload: {e}")
        st.warning("The image could not be uploaded. Your saved recipe will use a placeholder.")
        return None
