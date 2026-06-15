═══════════════════════════════════════════════════════════════════════
MODE: PERCEPTION-ISOLATED — YOU DO NOT GET OBJECT WORLD COORDINATES
═══════════════════════════════════════════════════════════════════════

The state JSON only gives you object_names + robot proprioception (NO xyz
per object). You must LOCALIZE objects yourself via camera + depth:

  HOW TO GET AN OBJECT'S WORLD XYZ:
  1. Look at images_cam/image_cam_NN.png (calibration frame — the SECOND
     image returned by view_driver_state and by every primitive tool).
     Find the target object's pixel (row from top, col from left; image
     is 256×256).
  2. Call back_project(row, col) to back-project that pixel ->
     world_xyz using the metric depth at that pixel + camera_meta.
  3. Sample 3-5 pixels on the object and median their xy for robustness.
  4. For z (grasp height): sample the table surface next to the object
     (not the object itself). Then add ~0.02-0.05 m for pre-pos height.

  CRITICAL: images/image_NN.png is the Pi0 frame (180° rotated) — do NOT
  pick pixels from it for back-projection. Use images_cam/image_cam_NN.png
  ONLY.

  view_camera_meta() returns the calibration: intrinsics K (3×3),
  extrinsic cam->world (4×4), and the projection recipe.

  KNOWN TABLE HEIGHTS (sanity-check your back-projected z):
    • KITCHEN frame  (eef_z ≈ 1.17):  table ≈ 0.90 m
    • LIVING_ROOM    (eef_z ≈ 0.68):  table ≈ 0.42 m
    • Object scene   (eef_z ≈ 0.26):  table ≈ 0.05 m

ALWAYS verify your position by looking at images_cam/image_cam_NN.png after moving.
Apply manipulation offsets from memory (e.g. BOWL: eef_y = plate_y + 0.045).

