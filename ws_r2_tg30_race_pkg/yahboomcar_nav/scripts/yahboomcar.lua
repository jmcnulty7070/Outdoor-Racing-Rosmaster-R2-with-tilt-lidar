-- yahboomcar.lua  –  Cartographer 2D config for ROSMASTER R2 + TG30 tilted LiDAR
-- IMU ENABLED: The EKF-fused IMU (/imu/imu_data) is fed to Cartographer via
--   tracking_frame = "imu_link"
-- This significantly improves scan-to-scan rotation estimates on outdoor
-- sidewalks where the robot may pitch/roll slightly over curb edges.

include "map_builder.lua"
include "trajectory_builder.lua"

options = {
  map_builder                               = MAP_BUILDER,
  trajectory_builder                        = TRAJECTORY_BUILDER,
  map_frame                                 = "map",

  -- Use imu_link as tracking frame so Cartographer receives IMU orientation.
  -- The static TF base_link -> imu_link must be present (it is, via bringup).
  tracking_frame                            = "imu_link",

  published_frame                           = "odom",
  odom_frame                                = "odom",
  provide_odom_frame                        = false,   -- EKF provides odom; don't double-publish
  publish_frame_projected_to_2d             = true,    -- flatten to 2D for map building

  use_odometry                              = true,
  use_nav_sat                               = false,
  use_landmarks                             = false,

  num_laser_scans                           = 1,
  num_multi_echo_laser_scans                = 0,
  num_subdivisions_per_laser_scan           = 1,
  num_point_clouds                          = 0,

  lookup_transform_timeout_sec              = 0.20,
  submap_publish_period_sec                 = 0.30,
  pose_publish_period_sec                   = 5e-3,
  trajectory_publish_period_sec             = 30e-3,

  rangefinder_sampling_ratio                = 1.0,
  odometry_sampling_ratio                   = 0.5,
  fixed_frame_pose_sampling_ratio           = 1.0,
  imu_sampling_ratio                        = 1.0,   -- use every IMU sample
  landmarks_sampling_ratio                  = 1.0,
}

MAP_BUILDER.use_trajectory_builder_2d = true

-- -----------------------------------------------------------------------
-- 2D trajectory builder – tuned for outdoor sidewalk with tilted LiDAR
-- -----------------------------------------------------------------------
TRAJECTORY_BUILDER_2D.min_range                           = 0.12
TRAJECTORY_BUILDER_2D.max_range                           = 10.0
TRAJECTORY_BUILDER_2D.missing_data_ray_length             = 2.0

-- IMU ON: Cartographer will use IMU for angular pre-integration.
-- With IMU, online correlative scan matching can be lighter because
-- the initial rotation estimate is already good.
TRAJECTORY_BUILDER_2D.use_imu_data                        = true
TRAJECTORY_BUILDER_2D.imu_gravity_time_constant           = 10.0  -- seconds; outdoor default

-- Correlative scan matching is still useful for translation compensation
-- on uneven sidewalk surfaces.
TRAJECTORY_BUILDER_2D.use_online_correlative_scan_matching = true
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.linear_search_window   = 0.10
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.translation_delta_cost_weight = 10.0
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.rotation_delta_cost_weight    = 1e3  -- trust IMU more

-- Submaps: 45 scans per submap works well for driveway/sidewalk loops.
TRAJECTORY_BUILDER_2D.submaps.num_range_data              = 45
TRAJECTORY_BUILDER_2D.submaps.grid_options_2d.resolution  = 0.05

-- -----------------------------------------------------------------------
-- Pose graph
-- -----------------------------------------------------------------------
POSE_GRAPH.optimization_problem.huber_scale   = 1e2
POSE_GRAPH.optimize_every_n_nodes             = 35
POSE_GRAPH.constraint_builder.min_score       = 0.60

-- Tune IMU weight in the pose graph optimiser
POSE_GRAPH.optimization_problem.acceleration_weight = 1e3
POSE_GRAPH.optimization_problem.rotation_weight     = 3e5

return options
