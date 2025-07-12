
import easyocr
import cv2
import matplotlib.pyplot as plt

def run_ocr(image_path, show_image=False):
    """
    Runs OCR on the given image using EasyOCR.

    Args:
        image_path (str): Path to the image file.
        show_image (bool): Whether to display the image with bounding boxes. Default is False.

    Returns:
        List of tuples: Each tuple contains (bbox, text, confidence).
    """
    # Initialize EasyOCR Reader
    reader = easyocr.Reader(['en'])

    # Read text from image
    results = reader.readtext(image_path)

    # Optionally display image with bounding boxes
    if show_image:
        image = cv2.imread(image_path)
        for (bbox, text, prob) in results:
            (top_left, top_right, bottom_right, bottom_left) = bbox
            top_left = tuple(map(int, top_left))
            bottom_right = tuple(map(int, bottom_right))
            cv2.rectangle(image, top_left, bottom_right, (0, 255, 0), 2)
            cv2.putText(image, text, (top_left[0], top_left[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        plt.axis('off')
        plt.title('OCR Result')
        plt.show()

    return results

# Example usage
if __name__ == "__main__":
    import sys

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("image_path", help="Path to the image")
    parser.add_argument("--show", action="store_true", help="Display image with bounding boxes")
    args = parser.parse_args()

    output = run_ocr(args.image_path, show_image=args.show)
    for bbox, text, conf in output:
        print(f"Detected: '{text}' with confidence {conf:.2f}")
 
