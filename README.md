# ROSMASTER R2 TG30 Race Workspace

This zip gives you a **separate ROS1 catkin workspace** for mapping, localization, waypoint making, and racing with a **tilted YDLIDAR TG30** on a real car.

## What this workspace is for

This workspace is meant for a ROSMASTER R2 style car that uses:

- **ROS1 Noetic** on Ubuntu 20.04
- **YDLIDAR TG30**
- LiDAR mounted about **4.5 inches above the ground**
- LiDAR tilted **down 5 degrees**
- Car frame name **`base_link`**
- LiDAR frame name **`lidar_link`**
- Main scan topic **`/scan`**
- Main drive command topic **`/cmd_vel`**
- An odometry topic **`/odom`**
- Optional IMU topic **`/imu/data`**

This setup is designed to help you:

1. **Drive and map** your driveway and sidewalk
2. **Record bags** while you drive
3. **Make a waypoint path**
4. **Localize** later with AMCL
5. **Race the path** with pure pursuit
6. **Avoid new obstacles** with follow-the-gap (FTG)

---

## Big idea in simple words

Think of the system as 4 layers:

### Layer 1: See the world
The TG30 looks at the ground and obstacles.

### Layer 2: Clean the scan
Because your LiDAR is tilted down, some rays may hit the ground too much.  
So we:

- filter the raw scan
- turn it into a point cloud
- slice out a useful band
- turn that back into a cleaner scan for mapping and obstacle use

### Layer 3: Learn the course
You can drive the car once and:

- record a rosbag
- save a map
- save waypoint points from odom

### Layer 4: Race the course
During replay on the real car:

- **Pure pursuit** tries to follow the path smoothly
- **FTG** watches for surprise obstacles
- **Steering modifier / arbiter** chooses a safe final `/cmd_vel`

So the car follows the path **unless** something is in the way.  
Then FTG helps it dodge around the obstacle.

---

## Folder layout

```text
ws_r2_tg30_race_pkg/
├── README.md
└── src/
    ├── ydlidar_ros_driver/
    │   └── README_EXTERNAL_DRIVER.md
    └── r2_tg30_race/
        ├── CMakeLists.txt
        ├── package.xml
        ├── launch/
        ├── config/
        ├── scripts/
        ├── urdf/
        ├── maps/
        ├── bags/
        └── waypoints/
```

---

## Important safety rules

Please use these the first time you test on the real car:

- Put the car on a stand first so the wheels can spin safely.
- Keep one person ready to stop the car.
- Start with low speed.
- Test LiDAR, odom, and `/cmd_vel` one at a time.
- Make sure left/right steering direction is correct.
- Make sure forward motion is really forward in odom.
- Do not test near traffic.
- Do not let the car run fully autonomous until teleop and stop behavior are proven.

---

## Assumptions used in this package

I used these defaults because they were either requested or not fully specified:

- **ROS distro:** Noetic
- **Workspace path:** `~/ws_r2_tg30_race_pkg`
- **Drive style:** Ackermann-style car, but command output stays on standard ROS **`/cmd_vel`**
- **LiDAR topic:** `/scan`
- **Base frame:** `base_link`
- **Laser frame:** `lidar_link`
- **Map frame:** `map`
- **Odom frame:** `odom`
- **Odom exists:** yes
- **IMU exists:** optional, not required by these nodes
- **TG30 port:** default `/dev/ydlidar` with fallback to `/dev/ttyUSB0`
- **Forward LiDAR offset:** `x = 0.20 m`
- **Height:** `z = 0.1143 m`
- **Pitch:** `-5 deg`

---

## Install system packages

Run these commands in a terminal.

```bash
sudo apt update

sudo apt install -y   ros-noetic-desktop-full   python3-catkin-tools   ros-noetic-laser-filters   ros-noetic-pointcloud-to-laserscan   ros-noetic-slam-gmapping   ros-noetic-amcl   ros-noetic-map-server   ros-noetic-octomap-server   ros-noetic-laser-geometry   ros-noetic-pcl-ros   ros-noetic-tf2-ros   ros-noetic-tf   ros-noetic-robot-state-publisher   ros-noetic-joint-state-publisher   ros-noetic-rosbag   ros-noetic-roslint
```

If you already have ROS Noetic installed, you mostly just need the package list above.

---

## About the YDLIDAR driver

This zip includes a folder called:

```text
src/ydlidar_ros_driver/
```

That folder is a **placeholder** so this workspace layout matches your request.

You have **2 choices**:

### Choice A: install the driver from apt or your existing system
If your TG30 driver is already installed and publishes `/scan`, you can use:

```bash
roslaunch r2_tg30_race tg30_bringup.launch start_driver:=false
```

### Choice B: replace the placeholder with the real upstream driver
Delete the placeholder folder and clone the real driver into `src/`:

```bash
cd ~/ws_r2_tg30_race_pkg/src
rm -rf ydlidar_ros_driver
git clone https://github.com/YDLIDAR/ydlidar_ros_driver.git
```

Then build again.

---

## Build this workspace without touching your other workspaces

This does **not** edit your `.bashrc`.

```bash
mkdir -p ~/ws_r2_tg30_race_pkg/src
cd ~/ws_r2_tg30_race_pkg

catkin_make

source devel/setup.bash
```

If you prefer `catkin build`:

```bash
cd ~/ws_r2_tg30_race_pkg
catkin init
catkin build
source devel/setup.bash
```

You only source this workspace in the terminal you want to use.

---

## Quick first test plan

### 1) Start ROS master
```bash
roscore
```

### 2) In a new terminal, source the workspace
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
```

### 3) Start the TG30 + static TF
If the driver is external or already installed:
```bash
roslaunch r2_tg30_race tg30_bringup.launch start_driver:=false
```

If the real `ydlidar_ros_driver` package is present in the workspace:
```bash
roslaunch r2_tg30_race tg30_bringup.launch start_driver:=true
```

### 4) Look at the scan
```bash
rostopic echo /scan
```

### 5) Start scan cleanup
```bash
roslaunch r2_tg30_race scan_cleanup.launch
```

### 6) Check the cleaned obstacle scan
```bash
rostopic echo /scan_obstacles
```

---

## How mapping works

The tilted LiDAR can still help you map, but the raw scan may include ground clutter.

This package does:

```text
/scan
  -> laser_filters
  -> /scan_filtered
  -> scan_to_cloud.py
  -> /scan_cloud
  -> pointcloud_to_laserscan
  -> /scan_obstacles
```

Then `gmapping` can use `/scan_obstacles`.

### Start mapping
```bash
roslaunch r2_tg30_race mapping_gmapping.launch
```

Drive the car slowly around the driveway and sidewalk.

### Save the map
When the map looks good:

```bash
rosrun map_server map_saver -f ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/maps/driveway_course
```

That creates:

- `driveway_course.pgm`
- `driveway_course.yaml`

---

## Record a rosbag while driving

### Simple direct rosbag command
```bash
rosbag record -O ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/bags/course_run.bag   /scan /scan_filtered /scan_obstacles /tf /odom /cmd_vel /joy /imu/data
```

### Or use the included helper node
The helper node listens on `/bag_record_cmd` with `std_msgs/Bool`.

Start the helper:
```bash
rosrun r2_tg30_race bag_control_recorder.py
```

Start recording:
```bash
rostopic pub /bag_record_cmd std_msgs/Bool "data: true" -1
```

Stop recording:
```bash
rostopic pub /bag_record_cmd std_msgs/Bool "data: false" -1
```

---

## Make waypoints while driving

The node `waypoint_extractor.py` watches `/odom`.

It saves a new waypoint every time the car moves far enough.

### Start waypoint extraction
```bash
rosrun r2_tg30_race waypoint_extractor.py _sample_distance:=0.40
```

This publishes:

- `/waypoint_path`

And saves:

- `src/r2_tg30_race/waypoints/waypoints.yaml`

### Manual mark button
It also listens for manual marks on:

- `/waypoint_mark` as `std_msgs/Empty`

Add a point manually:

```bash
rostopic pub /waypoint_mark std_msgs/Empty "{}" -1
```

---

## Publish a saved waypoint path

After you have a YAML file of waypoints:

```bash
rosrun r2_tg30_race waypoint_map_builder.py   _yaml_file:=~/ws_r2_tg30_race_pkg/src/r2_tg30_race/waypoints/waypoints.yaml
```

That publishes:

- `/race_path` as `nav_msgs/Path`

---

## Localization later with AMCL

Once you have a saved map, you can localize with the cleaned obstacle scan.

### Start localization
```bash
roslaunch r2_tg30_race localization_amcl.launch   map_file:=~/ws_r2_tg30_race_pkg/src/r2_tg30_race/maps/driveway_course.yaml
```

### Set the starting pose
In RViz, use **2D Pose Estimate** to place the car on the map.

---

## Race the path on the real car

This is the important part.

### What each node does

#### Pure pursuit
Looks at the saved path and tries to drive toward a point ahead on the path.

#### Follow-the-gap (FTG)
Looks at the LiDAR and finds the safest open gap.

#### Steering modifier / arbiter
Blends both ideas:

- if the path is clear, mostly follow pure pursuit
- if an obstacle is close, use FTG more
- slow down when things get tight

### Start the race stack
```bash
roslaunch r2_tg30_race racing_stack.launch   waypoint_yaml:=~/ws_r2_tg30_race_pkg/src/r2_tg30_race/waypoints/waypoints.yaml
```

### Main topics in the racing stack

- `/race_path` — saved path
- `/pp_cmd_vel` — pure pursuit suggestion
- `/ftg_cmd_vel` — obstacle avoidance suggestion
- `/cmd_vel` — final command sent to the car

---

## Very safe first driving order

Use this order on the real car:

### Step 1: pure pursuit only
Set a very open area and confirm the car follows the path.

### Step 2: FTG only
Place a box or cone in front and confirm the car turns away.

### Step 3: arbiter
Turn on the full stack and confirm:
- it follows the path
- it slows near obstacles
- it avoids the obstacle instead of pushing into it

---

## Rosbag replay

You can test a lot without moving the real car.

### Replay with simulated time
```bash
rosparam set use_sim_time true
rosbag play --clock ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/bags/course_run.bag
```

Then start your nodes in other terminals.

When done:
```bash
rosparam set use_sim_time false
```

---

## Conservative Jetson Orin Nano CPU notes

These are not hard guarantees. They are just safe expectations for this lightweight stack.

- `laser_filters`: low CPU
- `scan_to_cloud.py`: low to medium CPU
- `pointcloud_to_laserscan`: low to medium CPU
- `gmapping`: medium CPU
- `amcl`: low to medium CPU
- `pure_pursuit_twist.py`: low CPU
- `follow_the_gap.py`: low CPU
- `steering_modifier.py`: very low CPU
- `octomap_server`: medium to high CPU, optional

### Good rule
For racing, use only what you need:

- real driver
- scan cleanup
- waypoint path publisher
- pure pursuit
- FTG
- steering modifier

Do not run heavy extra tools unless you need them.

---

## Recommended launch order on the real car

### Mapping day
1. `roscore`
2. `tg30_bringup.launch`
3. `scan_cleanup.launch`
4. `mapping_gmapping.launch`
5. `waypoint_extractor.py`
6. `rosbag record ...`

### Localization day
1. `roscore`
2. `tg30_bringup.launch`
3. `scan_cleanup.launch`
4. `localization_amcl.launch`

### Racing day
1. `roscore`
2. `tg30_bringup.launch`
3. `scan_cleanup.launch`
4. `localization_amcl.launch`
5. `racing_stack.launch`

---

## Tuning tips

### If the map looks messy
- lower speed
- reduce near-ground clutter
- tighten pointcloud height slice
- confirm TF is correct
- check LiDAR pitch sign

### If pure pursuit cuts corners too much
- reduce lookahead distance
- reduce speed
- increase path waypoint density

### If FTG turns too late
- increase `danger_distance`
- increase front focus window
- slow down in tight spaces

### If the car wiggles
- lower angular gain
- reduce speed
- smooth odom
- smooth steering in your motor layer if available

---

## Real car checklist

Before autonomous driving, confirm all of these:

- `/scan` exists
- `/scan_obstacles` exists
- `/odom` moves forward when the car moves forward
- `base_link` and `lidar_link` TF are correct
- path is published on `/race_path`
- pure pursuit publishes `/pp_cmd_vel`
- FTG publishes `/ftg_cmd_vel`
- arbiter publishes `/cmd_vel`
- emergency stop method is ready
- wheel direction is correct

---

## Files you will care about most

- `src/r2_tg30_race/launch/racing_stack.launch`
- `src/r2_tg30_race/config/pure_pursuit.yaml`
- `src/r2_tg30_race/config/follow_the_gap.yaml`
- `src/r2_tg30_race/config/steering_modifier.yaml`
- `src/r2_tg30_race/scripts/pure_pursuit_twist.py`
- `src/r2_tg30_race/scripts/follow_the_gap.py`
- `src/r2_tg30_race/scripts/steering_modifier.py`

---

## Last note

This package is made to be a **clean starting point**.  
It keeps your old workspaces safe and separate.

The next best step after this would be:
- add RViz displays
- add a joystick deadman switch
- convert `/cmd_vel` to your exact Ackermann motor controller interface
- tune the FTG danger distance for sidewalk driving
