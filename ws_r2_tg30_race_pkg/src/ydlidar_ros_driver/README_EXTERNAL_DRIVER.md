# Placeholder for YDLIDAR ROS Driver

This folder is only a placeholder so the workspace layout matches the requested zip structure.

## Replace it with the real driver

```bash
cd ~/ws_r2_tg30_race_pkg/src
rm -rf ydlidar_ros_driver
git clone https://github.com/YDLIDAR/ydlidar_ros_driver.git
```

Then rebuild:

```bash
cd ~/ws_r2_tg30_race_pkg
catkin_make
source devel/setup.bash
```

## Or keep your existing installed driver

If your system already has a working TG30 ROS driver that publishes `/scan`, you can simply launch:

```bash
roslaunch r2_tg30_race tg30_bringup.launch start_driver:=false
```
