# TG30 Sidewalk Racer Complete README

> Full ROS1 Melodic package for Yahboom R2 / ROSMASTER R2 using TG30 tilted 5°, IMU, wheel odometry, Cartographer, EKF, /scan_mapping, and /scan_racing.

---

## Original Full Build Notes

```text
Below is a complete ROS1 Melodic starting package for:

TG30 tilted 5°
+ IMU
+ wheel odom
+ Cartographer
+ EKF
+ /scan_mapping
+ /scan_racing

Assumed topics:

/tg30/scan_raw     raw TG30 scan
/scan_mapping      Cartographer scan
/scan_racing       FTG / obstacle scan
/imu/data          IMU data
/wheel/odom        wheel odometry input
/odometry/filtered EKF output
1. Create package
cd ~/catkin_ws/src
catkin_create_pkg tg30_sidewalk_racer rospy sensor_msgs nav_msgs robot_localization
mkdir -p tg30_sidewalk_racer/scripts
mkdir -p tg30_sidewalk_racer/config
mkdir -p tg30_sidewalk_racer/launch
2. Python scan splitter/filter node
nano ~/catkin_ws/src/tg30_sidewalk_racer/scripts/tg30_scan_splitter.py

Paste:

#!/usr/bin/env python
import rospy
import math
from sensor_msgs.msg import LaserScan


class TG30ScanSplitter:
    def __init__(self):
        self.raw_topic = rospy.get_param("~raw_topic", "/tg30/scan_raw")
        self.mapping_topic = rospy.get_param("~mapping_topic", "/scan_mapping")
        self.racing_topic = rospy.get_param("~racing_topic", "/scan_racing")

        self.mapping_min = rospy.get_param("~mapping_min_range", 0.18)
        self.mapping_max = rospy.get_param("~mapping_max_range", 7.0)
        self.mapping_angle = math.radians(rospy.get_param("~mapping_keep_angle_deg", 120.0))
        self.mapping_median = rospy.get_param("~mapping_median_window", 3)

        self.racing_min = rospy.get_param("~racing_min_range", 0.22)
        self.racing_max = rospy.get_param("~racing_max_range", 5.0)
        self.racing_angle = math.radians(rospy.get_param("~racing_keep_angle_deg", 105.0))
        self.racing_median = rospy.get_param("~racing_median_window", 5)
        self.racing_cluster_points = rospy.get_param("~racing_cluster_min_points", 4)

        self.pub_mapping = rospy.Publisher(self.mapping_topic, LaserScan, queue_size=10)
        self.pub_racing = rospy.Publisher(self.racing_topic, LaserScan, queue_size=10)

        self.sub = rospy.Subscriber(self.raw_topic, LaserScan, self.cb, queue_size=10)

        rospy.loginfo("TG30 scan splitter started")
        rospy.loginfo("Raw:     %s", self.raw_topic)
        rospy.loginfo("Mapping: %s", self.mapping_topic)
        rospy.loginfo("Racing:  %s", self.racing_topic)

    def valid(self, r, rmin, rmax):
        return math.isfinite(r) and rmin <= r <= rmax

    def median_filter(self, values, window, rmin, rmax):
        if window < 3:
            return values

        half = window // 2
        out = list(values)

        for i in range(len(values)):
            local = []
            for j in range(i - half, i + half + 1):
                if 0 <= j < len(values):
                    if self.valid(values[j], rmin, rmax):
                        local.append(values[j])
            if len(local) >= 2:
                local.sort()
                out[i] = local[len(local) // 2]

        return out

    def remove_isolated_points(self, values, rmin, rmax, cluster_min):
        out = list(values)

        for i in range(len(values)):
            if not self.valid(values[i], rmin, rmax):
                continue

            count = 0
            for j in range(i - cluster_min, i + cluster_min + 1):
                if 0 <= j < len(values):
                    if self.valid(values[j], rmin, rmax):
                        if abs(values[j] - values[i]) < 0.35:
                            count += 1

            if count < cluster_min:
                out[i] = float("inf")

        return out

    def make_filtered_scan(self, scan, rmin, rmax, keep_angle, median_window, racing=False):
        out = LaserScan()
        out.header = scan.header
        out.angle_min = scan.angle_min
        out.angle_max = scan.angle_max
        out.angle_increment = scan.angle_increment
        out.time_increment = scan.time_increment
        out.scan_time = scan.scan_time
        out.range_min = rmin
        out.range_max = rmax
        out.intensities = scan.intensities

        filtered = []

        for i, r in enumerate(scan.ranges):
            angle = scan.angle_min + i * scan.angle_increment

            if abs(angle) > keep_angle:
                filtered.append(float("inf"))
                continue

            if not self.valid(r, rmin, rmax):
                filtered.append(float("inf"))
                continue

            filtered.append(r)

        filtered = self.median_filter(filtered, median_window, rmin, rmax)

        if racing:
            filtered = self.remove_isolated_points(
                filtered,
                rmin,
                rmax,
                self.racing_cluster_points
            )

        out.ranges = filtered
        return out

    def cb(self, scan):
        mapping = self.make_filtered_scan(
            scan,
            self.mapping_min,
            self.mapping_max,
            self.mapping_angle,
            self.mapping_median,
            racing=False
        )

        racing = self.make_filtered_scan(
            scan,
            self.racing_min,
            self.racing_max,
            self.racing_angle,
            self.racing_median,
            racing=True
        )

        self.pub_mapping.publish(mapping)
        self.pub_racing.publish(racing)


if __name__ == "__main__":
    rospy.init_node("tg30_scan_splitter")
    TG30ScanSplitter()
    rospy.spin()

Make executable:

chmod +x ~/catkin_ws/src/tg30_sidewalk_racer/scripts/tg30_scan_splitter.py
3. Filter YAML
nano ~/catkin_ws/src/tg30_sidewalk_racer/config/tg30_filters.yaml

Paste:

tg30_scan_splitter:
  raw_topic: "/tg30/scan_raw"

  mapping_topic: "/scan_mapping"
  mapping_min_range: 0.18
  mapping_max_range: 7.0
  mapping_keep_angle_deg: 120.0
  mapping_median_window: 3

  racing_topic: "/scan_racing"
  racing_min_range: 0.22
  racing_max_range: 5.0
  racing_keep_angle_deg: 105.0
  racing_median_window: 5
  racing_cluster_min_points: 4
4. EKF config: IMU + wheel odom

Install if needed:

sudo apt install ros-melodic-robot-localization

Create:

nano ~/catkin_ws/src/tg30_sidewalk_racer/config/ekf_sidewalk.yaml

Paste:

frequency: 30
sensor_timeout: 0.2
two_d_mode: true
transform_time_offset: 0.0
transform_timeout: 0.1
print_diagnostics: true
debug: false

map_frame: map
odom_frame: odom
base_link_frame: base_link
world_frame: odom

# Wheel odom input
odom0: /wheel/odom
odom0_config: [
  true,  true,  false,   # x, y, z
  false, false, true,    # roll, pitch, yaw
  true,  true,  false,   # vx, vy, vz
  false, false, true,    # vroll, vpitch, vyaw
  false, false, false    # ax, ay, az
]
odom0_differential: false
odom0_relative: false
odom0_queue_size: 10
odom0_pose_rejection_threshold: 5.0
odom0_twist_rejection_threshold: 1.0

# IMU input
imu0: /imu/data
imu0_config: [
  false, false, false,   # x, y, z
  true,  true,  true,    # roll, pitch, yaw
  false, false, false,   # vx, vy, vz
  true,  true,  true,    # vroll, vpitch, vyaw
  true,  true,  false    # ax, ay, az
]
imu0_differential: false
imu0_relative: true
imu0_queue_size: 20
imu0_remove_gravitational_acceleration: true
imu0_pose_rejection_threshold: 0.8
imu0_twist_rejection_threshold: 0.8
imu0_linear_acceleration_rejection_threshold: 1.5

process_noise_covariance: [
  0.05, 0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,
  0,    0.05, 0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,
  0,    0,    0.06, 0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,
  0,    0,    0,    0.03, 0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,
  0,    0,    0,    0,    0.03, 0,    0,    0,    0,    0,    0,    0,    0,    0,    0,
  0,    0,    0,    0,    0,    0.04, 0,    0,    0,    0,    0,    0,    0,    0,    0,
  0,    0,    0,    0,    0,    0,    0.08, 0,    0,    0,    0,    0,    0,    0,    0,
  0,    0,    0,    0,    0,    0,    0,    0.08, 0,    0,    0,    0,    0,    0,    0,
  0,    0,    0,    0,    0,    0,    0,    0,    0.06, 0,    0,    0,    0,    0,    0,
  0,    0,    0,    0,    0,    0,    0,    0,    0,    0.04, 0,    0,    0,    0,    0,
  0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0.04, 0,    0,    0,    0,
  0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0.05, 0,    0,    0,
  0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0.10, 0,    0,
  0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0.10, 0,
  0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0.10
]

initial_estimate_covariance: [
  1e-9, 0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,
  0,    1e-9, 0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,
  0,    0,    1e-9, 0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,
  0,    0,    0,    1e-9, 0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,
  0,    0,    0,    0,    1e-9, 0,    0,    0,    0,    0,    0,    0,    0,    0,    0,
  0,    0,    0,    0,    0,    1e-9, 0,    0,    0,    0,    0,    0,    0,    0,    0,
  0,    0,    0,    0,    0,    0,    1e-9, 0,    0,    0,    0,    0,    0,    0,    0,
  0,    0,    0,    0,    0,    0,    0,    1e-9, 0,    0,    0,    0,    0,    0,    0,
  0,    0,    0,    0,    0,    0,    0,    0,    1e-9, 0,    0,    0,    0,    0,    0,
  0,    0,    0,    0,    0,    0,    0,    0,    0,    1e-9, 0,    0,    0,    0,    0,
  0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    1e-9, 0,    0,    0,    0,
  0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    1e-9, 0,    0,    0,
  0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    1e-9, 0,    0,
  0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    1e-9, 0,
  0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    1e-9
]
5. Cartographer mapping Lua with IMU
nano ~/catkin_ws/src/tg30_sidewalk_racer/config/tg30_sidewalk_mapping_imu.lua

Paste:

include "map_builder.lua"
include "trajectory_builder.lua"

options = {
  map_builder = MAP_BUILDER,
  trajectory_builder = TRAJECTORY_BUILDER,

  map_frame = "map",
  tracking_frame = "imu_link",
  published_frame = "base_link",
  odom_frame = "odom",

  provide_odom_frame = false,
  publish_frame_projected_to_2d = true,

  use_odometry = true,
  use_nav_sat = false,
  use_landmarks = false,

  num_laser_scans = 1,
  num_multi_echo_laser_scans = 0,
  num_subdivisions_per_laser_scan = 1,
  num_point_clouds = 0,

  lookup_transform_timeout_sec = 0.2,
  submap_publish_period_sec = 0.5,
  pose_publish_period_sec = 0.02,
  trajectory_publish_period_sec = 0.05,

  rangefinder_sampling_ratio = 1.0,
  odometry_sampling_ratio = 1.0,
  fixed_frame_pose_sampling_ratio = 1.0,
  imu_sampling_ratio = 1.0,
  landmarks_sampling_ratio = 1.0,
}

MAP_BUILDER.use_trajectory_builder_2d = true

-- IMU ON for tilted outdoor LiDAR
TRAJECTORY_BUILDER_2D.use_imu_data = true

-- TG30 tilted sidewalk settings
TRAJECTORY_BUILDER_2D.min_range = 0.18
TRAJECTORY_BUILDER_2D.max_range = 7.0
TRAJECTORY_BUILDER_2D.missing_data_ray_length = 3.0
TRAJECTORY_BUILDER_2D.voxel_filter_size = 0.05

-- Outdoor sidewalk: smaller submaps adapt better to turns and grass edges
TRAJECTORY_BUILDER_2D.submaps.num_range_data = 60

-- Do not over-trust noisy grass returns
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.translation_weight = 8.0
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.rotation_weight = 35.0

-- Keep map updates responsive but not jittery
TRAJECTORY_BUILDER_2D.motion_filter.max_time_seconds = 0.5
TRAJECTORY_BUILDER_2D.motion_filter.max_distance_meters = 0.08
TRAJECTORY_BUILDER_2D.motion_filter.max_angle_radians = math.rad(1.0)

POSE_GRAPH.optimize_every_n_nodes = 90
POSE_GRAPH.constraint_builder.min_score = 0.55
POSE_GRAPH.constraint_builder.global_localization_min_score = 0.60

return options
6. Cartographer localization Lua with IMU
nano ~/catkin_ws/src/tg30_sidewalk_racer/config/tg30_sidewalk_localization_imu.lua

Paste:

include "map_builder.lua"
include "trajectory_builder.lua"

options = {
  map_builder = MAP_BUILDER,
  trajectory_builder = TRAJECTORY_BUILDER,

  map_frame = "map",
  tracking_frame = "imu_link",
  published_frame = "base_link",
  odom_frame = "odom",

  provide_odom_frame = false,
  publish_frame_projected_to_2d = true,

  use_odometry = true,
  use_nav_sat = false,
  use_landmarks = false,

  num_laser_scans = 1,
  num_multi_echo_laser_scans = 0,
  num_subdivisions_per_laser_scan = 1,
  num_point_clouds = 0,

  lookup_transform_timeout_sec = 0.2,
  submap_publish_period_sec = 0.5,
  pose_publish_period_sec = 0.02,
  trajectory_publish_period_sec = 0.05,

  rangefinder_sampling_ratio = 1.0,
  odometry_sampling_ratio = 1.0,
  fixed_frame_pose_sampling_ratio = 1.0,
  imu_sampling_ratio = 1.0,
  landmarks_sampling_ratio = 1.0,
}

MAP_BUILDER.use_trajectory_builder_2d = true

-- Localization mode
TRAJECTORY_BUILDER.pure_localization = true

TRAJECTORY_BUILDER_2D.use_imu_data = true
TRAJECTORY_BUILDER_2D.min_range = 0.18
TRAJECTORY_BUILDER_2D.max_range = 7.0
TRAJECTORY_BUILDER_2D.missing_data_ray_length = 3.0
TRAJECTORY_BUILDER_2D.voxel_filter_size = 0.05

-- Slightly stronger scan matching for racing localization
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.translation_weight = 10.0
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.rotation_weight = 40.0

TRAJECTORY_BUILDER_2D.motion_filter.max_time_seconds = 0.3
TRAJECTORY_BUILDER_2D.motion_filter.max_distance_meters = 0.05
TRAJECTORY_BUILDER_2D.motion_filter.max_angle_radians = math.rad(0.7)

POSE_GRAPH.optimize_every_n_nodes = 30
POSE_GRAPH.constraint_builder.min_score = 0.60
POSE_GRAPH.constraint_builder.global_localization_min_score = 0.65

return options
7. Static TF for tilted TG30 and IMU

Create:

nano ~/catkin_ws/src/tg30_sidewalk_racer/launch/tf_tg30_imu.launch

Paste:

<launch>
  <!-- base_link to tilted TG30 lidar_link -->
  <!-- xyz: 5.4 in forward, 0 side, 5.8 in high -->
  <!-- rpy: 0, -5 deg, 0 -->
  <node pkg="tf"
        type="static_transform_publisher"
        name="base_to_tg30_lidar"
        args="0.137 0.0 0.147 0 -0.0872665 0 base_link lidar_link 100" />

  <!-- Adjust these if your IMU is mounted elsewhere -->
  <node pkg="tf"
        type="static_transform_publisher"
        name="base_to_imu"
        args="0.0 0.0 0.10 0 0 0 base_link imu_link 100" />
</launch>
8. Scan splitter launch
nano ~/catkin_ws/src/tg30_sidewalk_racer/launch/tg30_scan_splitter.launch

Paste:

<launch>
  <rosparam file="$(find tg30_sidewalk_racer)/config/tg30_filters.yaml" command="load" />

  <node pkg="tg30_sidewalk_racer"
        type="tg30_scan_splitter.py"
        name="tg30_scan_splitter"
        output="screen">

    <param name="raw_topic" value="/tg30/scan_raw"/>

    <param name="mapping_topic" value="/scan_mapping"/>
    <param name="mapping_min_range" value="0.18"/>
    <param name="mapping_max_range" value="7.0"/>
    <param name="mapping_keep_angle_deg" value="120.0"/>
    <param name="mapping_median_window" value="3"/>

    <param name="racing_topic" value="/scan_racing"/>
    <param name="racing_min_range" value="0.22"/>
    <param name="racing_max_range" value="5.0"/>
    <param name="racing_keep_angle_deg" value="105.0"/>
    <param name="racing_median_window" value="5"/>
    <param name="racing_cluster_min_points" value="4"/>
  </node>
</launch>
9. EKF launch
nano ~/catkin_ws/src/tg30_sidewalk_racer/launch/ekf_sidewalk.launch

Paste:

<launch>
  <node pkg="robot_localization"
        type="ekf_localization_node"
        name="ekf_sidewalk"
        clear_params="true"
        output="screen">

    <rosparam command="load"
              file="$(find tg30_sidewalk_racer)/config/ekf_sidewalk.yaml" />

    <remap from="odometry/filtered" to="/odometry/filtered"/>
  </node>
</launch>
10. Cartographer mapping launch
nano ~/catkin_ws/src/tg30_sidewalk_racer/launch/cartographer_mapping_tg30_imu.launch

Paste:

<launch>
  <include file="$(find tg30_sidewalk_racer)/launch/tf_tg30_imu.launch"/>
  <include file="$(find tg30_sidewalk_racer)/launch/tg30_scan_splitter.launch"/>
  <include file="$(find tg30_sidewalk_racer)/launch/ekf_sidewalk.launch"/>

  <node pkg="cartographer_ros"
        type="cartographer_node"
        name="cartographer_node"
        args="-configuration_directory $(find tg30_sidewalk_racer)/config
              -configuration_basename tg30_sidewalk_mapping_imu.lua"
        output="screen">

    <remap from="scan" to="/scan_mapping"/>
    <remap from="odom" to="/odometry/filtered"/>
    <remap from="imu" to="/imu/data"/>
  </node>

  <node pkg="cartographer_ros"
        type="cartographer_occupancy_grid_node"
        name="cartographer_occupancy_grid_node"
        args="-resolution 0.05"
        output="screen"/>
</launch>
11. Cartographer localization launch

Use this after you already saved a .pbstream map.

nano ~/catkin_ws/src/tg30_sidewalk_racer/launch/cartographer_localization_tg30_imu.launch

Paste:

<launch>
  <arg name="pbstream" default="$(env HOME)/maps/sidewalk_map.pbstream"/>

  <include file="$(find tg30_sidewalk_racer)/launch/tf_tg30_imu.launch"/>
  <include file="$(find tg30_sidewalk_racer)/launch/tg30_scan_splitter.launch"/>
  <include file="$(find tg30_sidewalk_racer)/launch/ekf_sidewalk.launch"/>

  <node pkg="cartographer_ros"
        type="cartographer_node"
        name="cartographer_node"
        args="-configuration_directory $(find tg30_sidewalk_racer)/config
              -configuration_basename tg30_sidewalk_localization_imu.lua
              -load_state_filename $(arg pbstream)"
        output="screen">

    <remap from="scan" to="/scan_mapping"/>
    <remap from="odom" to="/odometry/filtered"/>
    <remap from="imu" to="/imu/data"/>
  </node>

  <node pkg="cartographer_ros"
        type="cartographer_occupancy_grid_node"
        name="cartographer_occupancy_grid_node"
        args="-resolution 0.05"
        output="screen"/>
</launch>
12. Build
cd ~/catkin_ws
catkin_make
source devel/setup.bash
13. Run order

Start Yahboom base, TG30, wheel odom, and IMU first.

Then mapping:

roslaunch tg30_sidewalk_racer cartographer_mapping_tg30_imu.launch

For racing/localization later:

roslaunch tg30_sidewalk_racer cartographer_localization_tg30_imu.launch
14. Important topic checks
rostopic echo /tg30/scan_raw --noarr
rostopic echo /scan_mapping --noarr
rostopic echo /scan_racing --noarr
rostopic echo /imu/data
rostopic echo /wheel/odom
rostopic echo /odometry/filtered

TF check:

rosrun tf view_frames
rosrun tf tf_echo base_link lidar_link
rosrun tf tf_echo base_link imu_link
rosrun tf tf_echo odom base_link
15. How this differs from standard Yahboom R2
Item	Standard flat Yahboom	Your tilted TG30 + IMU setup
LiDAR angle	Flat	5° downward
Raw scan	/scan	/tg30/scan_raw
Mapping scan	/scan	/scan_mapping
Racing scan	/scan	/scan_racing
Grass/curb edge	Often missed	Intentionally kept
Cartographer IMU	Often off	On
EKF	Sometimes odom only	wheel odom + IMU
FTG scan	raw scan	cleaned /scan_racing
Outdoor sidewalk noise	Poor handling	filtered and smoothed
Best use	indoor rooms	sidewalk racing
16. Most likely values you will tune first

If grass edge disappears:

mapping_median_window: 3
mapping_keep_angle_deg: 130.0
mapping_max_range: 8.0

If racing is twitchy:

racing_median_window: 7
racing_cluster_min_points: 5
racing_keep_angle_deg: 90.0

If Cartographer jitters:

TRAJECTORY_BUILDER_2D.motion_filter.max_distance_meters = 0.10
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.translation_weight = 12.0

If localization feels delayed:

TRAJECTORY_BUILDER_2D.motion_filter.max_time_seconds = 0.2

This gives you the full starting structure for the tilted TG30 sidewalk-racing stack.
```

---

## Recommended Folder Structure

```text
~/catkin_ws/src/tg30_sidewalk_racer/
├── scripts/
│   └── tg30_scan_splitter.py
├── config/
│   ├── tg30_filters.yaml
│   ├── ekf_sidewalk.yaml
│   ├── tg30_sidewalk_mapping_imu.lua
│   └── tg30_sidewalk_localization_imu.lua
└── launch/
    ├── tf_tg30_imu.launch
    ├── tg30_scan_splitter.launch
    ├── ekf_sidewalk.launch
    ├── cartographer_mapping_tg30_imu.launch
    └── cartographer_localization_tg30_imu.launch
```

---

## Quick Start

```bash
cd ~/catkin_ws
catkin_make
source devel/setup.bash
roslaunch tg30_sidewalk_racer cartographer_mapping_tg30_imu.launch
```

---

## Racing Mode

```bash
roslaunch tg30_sidewalk_racer cartographer_localization_tg30_imu.launch
```

---

## Important Topics

```text
/tg30/scan_raw
/scan_mapping
/scan_racing
/imu/data
/wheel/odom
/odometry/filtered
```

---

## Notes

This README preserves the entire original response exactly inside the code block above so nothing is lost.
