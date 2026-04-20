# ROSMASTER R2 TG30 Race Course README
<img width="1513" height="2017" alt="image" src="https://github.com/user-attachments/assets/1d39010a-185b-44f6-8fa5-59b21af234d8" />
This README matches the current state of this workspace as of `2026-04-20`.

It is written for a real ROSMASTER R2 running ROS Melodic.

## 1. Overview

This workspace is set up to:

1. Bring up the Yahboom R2 base, odometry, joystick, and robot TF
2. Start a forward-tilted TG30 LiDAR
3. Build a map with Cartographer
4. Save waypoints for a path
5. Localize on a saved map with AMCL
6. Drive the path using Pure Pursuit plus Follow The Gap (FTG)

Main custom package:

- `r2_tg30_race`

Main Yahboom packages used with it:

- `yahboomcar_bringup`
- `yahboomcar_description`
- `yahboomcar_nav`
- `yahboomcar_ctrl`

## 2. Main bringup idea

Use this as the real-car base launch:

```bash
roslaunch yahboomcar_bringup bringup.launch
```

That launch is the source for:

- base driver
- odometry
- joystick
- `robot_description`
- `robot_state_publisher`

Start the TG30 separately:

```bash
roslaunch r2_tg30_race tg30_bringup.launch start_driver:=true scan_topic:=/scan
```

Do not start two LiDAR drivers at the same time.

## 3. TF and LiDAR mount

The LiDAR mount transform is now owned by the URDF, not by a static TF node in `r2_tg30_race`.

Current TF path:

```text
yahboomcar_R2.urdf.xacro -> robot_description -> robot_state_publisher -> /tf
```

Relevant file:

- `src/yahboomcar_description/urdf/yahboomcar_R2.urdf.xacro`

Current LiDAR assumptions:

- frame: `laser_link`
- about `5.2 in` forward of the rear axle center
- about `6.0 in` above the rear axle center
- pitched forward about `5 degrees`

If `yahboomcar_bringup bringup.launch` is not running, you may be missing `base_link -> laser_link`.

## 4. ROS version and Python

This workspace is for ROS Melodic.

The custom `r2_tg30_race` scripts were cleaned up for Python 2.7 / Melodic style.

Many older Yahboom demo scripts were also switched from `python3` shebangs to `python2`, but some third-party libraries in vision packages may still be difficult to run on Python 2. The main race stack is the part that was cleaned up intentionally.

## 5. Build

Example workspace:

```bash
~/yahboomcar_ws
```

Build:

```bash
cd ~/yahboomcar_ws
catkin_make
```

Make all Python scripts under `src` executable:

```bash
find ~/yahboomcar_ws/src -type f -name "*.py" -exec chmod +x {} \;
```

Source every terminal:

```bash
source ~/yahboomcar_ws/devel/setup.bash
```

To source the workspace automatically in new terminals, add this to `~/.bashrc`:

```bash
echo "source ~/yahboomcar_ws/devel/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

## 6. Smoke test script

This workspace now includes a Linux-side smoke-test script at the workspace root:

- `test_stack.sh`

Use it on the real ROS Melodic machine after you build the workspace:

```bash
cd ~/yahboomcar_ws
chmod +x test_stack.sh
./test_stack.sh
```

If you already saved a map and want the AMCL smoke test too:

```bash
./test_stack.sh --map ~/yahboomcar_ws/src/r2_tg30_race/maps/driveway_course.yaml
```

What it checks:

- `catkin_make`
- xacro expansion of the R2 URDF
- launch-file parse checks for the main TG30 launches
- live no-hardware smoke launches for Cartographer, racing stack, and AMCL when a map is available
- expected nodes and key private params in `r2_tg30_race`

It writes logs under:

- `test_logs/`

## 7. Using Codex CLI

You can use Codex CLI to read this workspace, edit files, and check code from the terminal.

Simple idea:

1. open a terminal in the workspace
2. start Codex CLI
3. tell it what you want in plain English
4. let it inspect the code before editing

Start in the workspace root:

```bash
cd ~/yahboomcar_ws
```

Start Codex CLI:

```bash
codex
```

Good first prompts:

- `Inspect this ROS workspace. Do not edit anything yet. Tell me what packages control LiDAR, mapping, localization, joystick, motor control, URDF, and navigation.`
- `Check r2_tg30_race for obvious launch, TF, or topic problems. Do not edit yet.`
- `Review README_4_20_26.md and clean up stale instructions.`

If you want Codex to edit code, say exactly what you want changed:

- `Update r2_tg30_race to use Cartographer instead of gmapping.`
- `Add a mode light in the upper-right corner of the screen: red for manual, green for Pure Pursuit, blue for FTG.`
- `Tune follow_the_gap.yaml and steering_modifier.yaml so the car stays on the sidewalk and treats grass edges like barriers.`

If you want Codex to check code without changing anything, say that clearly:

- `Inspect only. Do not edit anything yet.`
- `Review this launch file and tell me what might break.`
- `Check whether this package still depends on Noetic features.`

If you want Codex to run checks on the Linux ROS machine, use prompts like:

- `Run the smoke test script and summarize the results.`
- `Check whether /scan, /odom, /joy, and base_link to laser_link are alive after bringup.`
- `Review the Cartographer launch and tell me if it stays up.`

Helpful rule:

- if you only want an explanation, say `do not edit`
- if you want changes made, say `go ahead and edit`
- if you want safety first, say `show me the files and risks before changing anything`

Codex works best when the request is short and specific.

Good:

- `Explain what racing_stack.launch does at an 8th grade level.`
- `Update the README to match the current TG30 setup.`
- `Find where the LiDAR TF is coming from.`

Less good:

- `fix everything`

When you are using the Linux robot computer, Codex can also help you run:

- `catkin_make`
- `roslaunch`
- `rostopic`
- `rosnode`
- `test_stack.sh`

That makes it useful for both editing code and checking whether the ROS stack is actually working.

## 8. Quick health check

After base bringup and TG30 bringup, these should exist:

- `/scan`
- `/joy`
- `/odom`
- `/tf`

Quick checks:

```bash
rostopic echo -n 1 /scan
rostopic echo -n 1 /joy
rostopic echo -n 1 /odom
```

If one is missing, fix that first before mapping or racing.

## 9. Mapping mode

`r2_tg30_race` now maps with Cartographer, not gmapping.

Primary launch:

```bash
roslaunch r2_tg30_race mapping_cartographer.launch start_driver:=false scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles
```

Compatibility alias:

```bash
roslaunch r2_tg30_race mapping_gmapping.launch start_driver:=false scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles
```

That old launch name now points to Cartographer internally.

Recommended mapping startup:

```bash
source ~/yahboomcar_ws/devel/setup.bash
roslaunch yahboomcar_bringup bringup.launch
```

```bash
source ~/yahboomcar_ws/devel/setup.bash
roslaunch r2_tg30_race tg30_bringup.launch start_driver:=true scan_topic:=/scan
```

```bash
source ~/yahboomcar_ws/devel/setup.bash
roslaunch r2_tg30_race mapping_cartographer.launch start_driver:=false scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles
```

Optional RViz:

```bash
source ~/yahboomcar_ws/devel/setup.bash
roslaunch r2_tg30_race view_mapping.launch
```

The TG30 RViz layouts were tuned for a top-down follow view:

- bright green `scan_obstacles` points to make grass edges and sidewalk boundaries easier to see
- the car model centered in view
- the race line shown in yellow when it is available
- AMCL red arrows in localization and racing views

What `mapping_cartographer.launch` does:

- starts TG30 only if `start_driver:=true`
- runs `scan_cleanup.launch`
- creates `/scan_obstacles`
- feeds `/scan_obstacles` into Cartographer

Save the map:

```bash
mkdir -p ~/yahboomcar_ws/src/r2_tg30_race/maps
rosrun map_server map_saver -f ~/yahboomcar_ws/src/r2_tg30_race/maps/driveway_course
```

That creates:

- `driveway_course.pgm`
- `driveway_course.yaml`

## 10. Cartographer files

Important files:

- `src/r2_tg30_race/launch/mapping_cartographer.launch`
- `src/yahboomcar_nav/scripts/yahboomcar.lua`

Current package dependency:

- `cartographer_ros`

Old dependency removed from `r2_tg30_race`:

- `slam_gmapping`

## 11. Waypoint recording

Record waypoints while driving slowly:

```bash
source ~/yahboomcar_ws/devel/setup.bash
rosrun r2_tg30_race waypoint_extractor.py _yaml_file:=/home/$USER/yahboomcar_ws/src/r2_tg30_race/waypoints/waypoints.yaml _path_topic:=/waypoint_path _sample_distance:=0.40
```

What it does:

- listens to `/odom`
- saves a waypoint about every `0.40 m`
- writes the YAML file while you drive

Manual mark topic:

```text
/waypoint_mark
```

Example:

```bash
rostopic pub /waypoint_mark std_msgs/Empty -1
```

## 12. Closed-loop path note

For a loop, you usually need to add the first waypoint again at the end of `waypoints.yaml`.

Why:

- `pure_pursuit_twist.py` treats the last waypoint like the finish line
- when it gets close enough, it stops

Rule of thumb:

- one-way route: do not repeat the first point
- loop route: repeat the first point at the end

## 13. Publish saved path by itself

The racing stack starts this automatically, but you can test it alone:

```bash
source ~/yahboomcar_ws/devel/setup.bash
rosrun r2_tg30_race waypoint_map_builder.py _yaml_file:=/home/$USER/yahboomcar_ws/src/r2_tg30_race/waypoints/waypoints.yaml _path_topic:=/race_path
```

Check:

```bash
rostopic echo -n 1 /race_path
```

## 14. Localization mode

Use this after you already have a saved map:

Stop `mapping_cartographer.launch` before starting AMCL.

Do not run Cartographer and AMCL at the same time on the real car. Cartographer is for building the map. AMCL is for localizing on a map you already saved.

```bash
source ~/yahboomcar_ws/devel/setup.bash
roslaunch yahboomcar_bringup bringup.launch
```

```bash
source ~/yahboomcar_ws/devel/setup.bash
roslaunch r2_tg30_race tg30_bringup.launch start_driver:=true scan_topic:=/scan
```

```bash
source ~/yahboomcar_ws/devel/setup.bash
roslaunch r2_tg30_race localization_amcl.launch start_driver:=false map_file:=/home/$USER/yahboomcar_ws/src/r2_tg30_race/maps/driveway_course.yaml scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles
```

Optional RViz:

```bash
source ~/yahboomcar_ws/devel/setup.bash
roslaunch r2_tg30_race view_localization.launch
```

Use RViz `2D Pose Estimate` if needed.

## 15. Racing mode

`racing_stack.launch` is the main path-driving mode.

Recommended startup:

```bash
source ~/yahboomcar_ws/devel/setup.bash
roslaunch yahboomcar_bringup bringup.launch
```

```bash
source ~/yahboomcar_ws/devel/setup.bash
roslaunch r2_tg30_race tg30_bringup.launch start_driver:=true scan_topic:=/scan
```

```bash
source ~/yahboomcar_ws/devel/setup.bash
roslaunch r2_tg30_race racing_stack.launch start_driver:=false scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles waypoint_yaml:=/home/$USER/yahboomcar_ws/src/r2_tg30_race/waypoints/waypoints.yaml use_ackermann_bridge:=true
```

Optional RViz:

```bash
source ~/yahboomcar_ws/devel/setup.bash
roslaunch r2_tg30_race view_racing.launch
```

`view_racing.launch` now also starts a small `2 in x 2 in` mode light in the upper-right corner of the screen.

Color meaning:

- red: manual control
- green: Pure Pursuit is the main active mode
- blue: FTG is taking over because nearby obstacles make the safety blend favor FTG

If you want RViz without the mode light:

```bash
roslaunch r2_tg30_race view_racing.launch show_mode_indicator:=false
```

What `racing_stack.launch` includes:

- `waypoint_map_builder.py` publishes `/race_path`
- `pure_pursuit_twist.py` publishes `/cmd_vel_auto_raw`
- `joy_deadman.py` publishes `/auto_enable`
- `cmdvel_gate.py` gates `/cmd_vel_auto_raw` into `/cmd_vel_auto`
- `follow_the_gap.py` publishes `/cmd_vel_ftg_raw`
- `steering_modifier.py` blends Pure Pursuit and FTG into `/cmd_vel_safety`
- `twist_mux` publishes final `/cmd_vel`
- `twist_to_ackermann.py` can publish `/ackermann_cmd`

## 16. Deadman switch

Current deadman setup:

- topic: `/joy`
- output: `/auto_enable`
- button index: `5`

Check it:

```bash
rostopic echo /auto_enable
```

Expected behavior:

- hold button: `data: true`
- release button: `data: false`

## 17. Topic checks before driving

Check these before real motion:

```bash
rostopic echo -n 1 /race_path
rostopic echo /auto_enable
rostopic echo /cmd_vel_auto_raw
rostopic echo /cmd_vel_auto
rostopic echo /cmd_vel_ftg_raw
rostopic echo /cmd_vel_safety
rostopic echo /cmd_vel
rostopic echo /ackermann_cmd
```

## 18. Important tuning files

### Pure Pursuit

- `src/r2_tg30_race/config/pure_pursuit.yaml`

Current key values:

- `lookahead_distance: 0.65`
- `base_speed: 0.45`
- `max_speed: 0.70`
- `goal_tolerance: 0.30`

### FTG

- `src/r2_tg30_race/config/follow_the_gap.yaml`

Current sidewalk-oriented values:

- `danger_distance: 1.10`
- `stop_distance: 0.45`
- `front_angle_deg: 110.0`
- `bubble_radius_idx: 14`
- `gap_threshold: 0.70`
- `max_speed: 0.40`
- `min_speed: 0.10`

### Steering modifier

- `src/r2_tg30_race/config/steering_modifier.yaml`

Current sidewalk-oriented values:

- `danger_distance: 1.10`
- `stop_distance: 0.45`
- `blend_distance: 1.60`
- `clear_path_speed_scale: 0.90`
- `danger_speed_scale: 0.25`
- `max_linear_x: 0.45`
- `front_fov_deg: 110.0`

The mode light uses the same steering-modifier distance thresholds to decide when to show green versus blue.

### Obstacle scan cleanup

- `src/r2_tg30_race/config/scan_filters.yaml`
- `src/r2_tg30_race/config/pointcloud_to_laserscan.yaml`

These are the main files that decide whether curb and grass-edge returns are kept or filtered out.

### Ackermann bridge

- `src/r2_tg30_race/config/ackermann_bridge.yaml`

Important values:

- `wheelbase: 0.26`
- `max_steering_angle: 0.45`
- `steering_sign: 1.0`

If steering is backwards, change `steering_sign` to `-1.0`.

## 19. Replay a bag later

```bash
roscore
```

```bash
rosbag play --clock ~/yahboomcar_ws/src/r2_tg30_race/bags/driveway_run.bag
```

If needed:

```bash
rosparam set use_sim_time true
```

Then launch mapping, localization, or racing tools.

## 20. Optional OctoMap

```bash
roslaunch r2_tg30_race octomap.launch
```

This uses `/scan_cloud`.

## 21. Safe shutdown order

1. Stop racing, mapping, or localization launches
2. Stop RViz
3. Stop rosbag recording
4. Stop `r2_tg30_race tg30_bringup.launch`
5. Stop `yahboomcar_bringup bringup.launch`
6. Stop `roscore` if you started it

## 22. Troubleshooting

### Problem: `/scan` is missing

Fix:

- check LiDAR cable and power
- check TG30 port and baudrate
- check that you started `tg30_bringup.launch` with `start_driver:=true`

### Problem: `/joy` is missing

Fix:

- check joystick connection
- check `yahboomcar_bringup bringup.launch`

### Problem: `/odom` is missing

Fix:

- the base driver is not publishing odometry yet
- Pure Pursuit and AMCL both need `/odom`

### Problem: deadman never goes true

Fix:

- check button index `5`
- watch `/joy` and see which button changes

### Problem: the mode light does not appear

Fix:

- make sure you launched `view_racing.launch`
- if needed, install `python-tk` on the Melodic machine
- if you do not want the light, run `show_mode_indicator:=false`

### Problem: car stops at the end of the path

Fix:

- for a loop track, add the first waypoint to the end of the file

### Problem: car turns the wrong way

Fix:

- change `steering_sign` in `ackermann_bridge.yaml`

### Problem: LiDAR ground clutter is too heavy

Fix:

- adjust physical tilt a little
- adjust `scan_filters.yaml`
- adjust `pointcloud_to_laserscan.yaml`
- drive slower while mapping

### Problem: TF error for `base_link` to `laser_link`

Fix:

- make sure `yahboomcar_bringup bringup.launch` is running
- make sure `robot_state_publisher` is alive
- do not expect `tg30_bringup.launch` to publish the LiDAR TF anymore

## 23. Common real workflow

1. Bring up the base:

```bash
roslaunch yahboomcar_bringup bringup.launch
```

2. Start the TG30:

```bash
roslaunch r2_tg30_race tg30_bringup.launch start_driver:=true
```

3. Make a map:

```bash
roslaunch r2_tg30_race mapping_cartographer.launch start_driver:=false scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles
```

4. Save the map:

```bash
rosrun map_server map_saver -f ~/yahboomcar_ws/src/r2_tg30_race/maps/driveway_course
```

5. Stop Cartographer before switching to AMCL localization.

6. Record waypoints:

```bash
rosrun r2_tg30_race waypoint_extractor.py _yaml_file:=/home/$USER/yahboomcar_ws/src/r2_tg30_race/waypoints/waypoints.yaml
```

7. For a loop, add the first waypoint to the end of the file.

8. Start AMCL localization if you want to drive on the saved map.

9. Run the race stack:

```bash
roslaunch r2_tg30_race racing_stack.launch start_driver:=false scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles waypoint_yaml:=/home/$USER/yahboomcar_ws/src/r2_tg30_race/waypoints/waypoints.yaml use_ackermann_bridge:=true
```

10. Hold the deadman button and test slowly while watching `/auto_enable`, `/cmd_vel`, and `/ackermann_cmd`.

If `view_racing.launch` is open, also watch the upper-right mode light:

- red for manual
- green for PP
- blue for FTG

## 24. Short version

Current real-car recommendation:

1. Use `yahboomcar_bringup bringup.launch` for base, odometry, and TF
2. Use `r2_tg30_race tg30_bringup.launch` for the TG30 driver
3. Use `mapping_cartographer.launch` for mapping
4. Use `localization_amcl.launch` for saved-map localization
5. Use `racing_stack.launch` for path driving
