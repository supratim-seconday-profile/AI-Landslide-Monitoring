from app.ml.predictor import predict_landslide


sample = {
    "B2": 0.20,
    "B3": 0.25,
    "B4": 0.22,
    "B5": 0.28,
    "B6": 0.35,
    "B7": 0.40,
    "B8": 0.42,
    "B8A": 0.45,
    "B11": 0.24,
    "B12": 0.18,
    "NDVI": 0.35,
    "NDMI": 0.18,
    "NDWI": -0.25,
    "NBR": 0.40,
    "hls_image_count": 360,
    "hls_valid_image_count": 12
}


print("=" * 60)
print("           SIH FINAL PREDICTOR TEST")
print("=" * 60)

result = predict_landslide(sample)

print()
print("Prediction result:")
print(result)

print()
print("=" * 60)
print("              TEST COMPLETE")
print("=" * 60)