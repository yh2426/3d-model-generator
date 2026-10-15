# 3D Model Generator

Double-click `Model_Generator_EN.html` and open it in Chrome or Edge. No installation, internet connection, or server is required.

1. The sample is Rectangular bar: width 100, depth 30, height 10 mm.
2. Optionally select a photo for local preview only.
3. Edit dimensions and switch between mm, cm, and inches.
4. Click Generate preview. This mock response loads the original sample.
5. Drag to rotate, scroll or use buttons to zoom, and use ↺ to reset.
6. Download STL or GLB. The page shows requested dimensions separately from actual sample dimensions.

## Rebuild the sample

Python 3.10+; no third-party dependencies. From the extracted folder:

```sh
python generate.py
python verify.py
python build_standalone.py
```

The final command updates `Model_Generator_EN.html`.

Edit `samples.json` to change dimensions. Update expected_volume_mm3 to width × depth × height, then regenerate. Coordinates in STL use mm; GLB uses meters and Y up.

Verification reopens both exports and checks dimensions, volume, connectivity, closed edges, winding, and geometric agreement. Expected dimensions: 100 × 30 × 10 mm. Volume: 30,000 mm³.

## Current scope

The UI uses mock responses. Editing form dimensions does not rebuild geometry. Photos do not generate geometry. The preview reads STL; GLB is available for download. Actual STL-to-GLB conversion and USDZ are not included yet.

The updated sample passed export geometry and JavaScript syntax checks. Updated offline browser interactions have not been retested. The package contains the current files and these run notes; earlier Phone Stand/Desk Organizer examples are not part of this demo.
