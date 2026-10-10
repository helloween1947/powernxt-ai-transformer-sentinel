# Original transformer geometry and asset review

Original local procedural distribution-transformer geometry in `src/components/digital-twin/TransformerScene.jsx`, refined on 10 October 2026. No external mesh, image, texture or downloadable model is used. The detailed model includes a ribbed oil tank, radiator fins and headers, cover bolts, lifting hardware, HV/LV porcelain bushings and terminals, conservator supports/filler, generic gauge, breather, drain valve, nameplate and base rails. It is a semantic illustration; sensor locations and asset-specific dimensions are unverified.

The preferred [CGTrader industrial distribution transformer](https://www.cgtrader.com/3d-models/industrial/industrial-machine/industrial-distribution-transformer) listing was inspected. At inspection it was a paid $4.99 royalty-free listing with 12,456 triangles, 2K PBR textures and blend/fbx/obj/gltf formats; its native package was listed as 375 MB. No licensed asset was supplied or acquired. No purchase or license acceptance occurred, and no preview mesh/image was extracted or hotlinked.

The three supplied Sketchfab candidates were investigated:

- https://sketchfab.com/3d-models/power-transformer-f26295e099e84f94b505079df49081d9
- https://sketchfab.com/3d-models/power-transformer-74fcc717921c47f786f1847108ba11a2
- https://sketchfab.com/3d-models/electrical-power-transformer-531ab7c5d8134809b7da8ef37a82f9b0

Their download/license suitability could not be verified through the available access. None is used. Replacement with an owned lawful local asset requires license/attribution verification, orientation/scale/framing and payload optimization before integration; geometry must preserve the semantic anchors.

Geometry is generated locally in a lazy JavaScript chunk. Demand rendering, capped DPR (desktop 1.5/mobile 1.2), one shadow map (1024/512), bounded opt-in orbit/zoom and no textures/post-processing constrain rendering work. WebGL/context failure shows a text availability state while measurement controls remain accessible. Context and media-query listeners clean up on unmount. No external model request occurs at runtime. Scene palette is centralized in `src/data/sceneMaterials.js` with matching CSS tokens.
