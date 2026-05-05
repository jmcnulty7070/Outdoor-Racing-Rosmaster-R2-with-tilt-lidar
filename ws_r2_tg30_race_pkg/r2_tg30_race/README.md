# ROSMASTER R2 Outdoor Racing Stack
### ROS Melodic · Ubuntu 18.04 · TG30 Tilted LiDAR

This package lets your R2 robot drive a race course on its own.
The steps are: build a map → record the path you want it to follow → close
the path into a loop → let it race.  You can take control any time by
moving the joystick.

---

## Before You Start — One-Time Setup

```bash
# Tell ROS which robot you have
export ROBOT_TYPE=R2
echo "export ROBOT_TYPE=R2" >> ~/.bashrc
source ~/.bashrc

# Build the workspace
cd ~/catkin_ws
catkin_make
source devel/setup.bash
```

---

## The One Launch File That Starts Everything

**`laser_bringup.launch`** is the single launch file you run at the start
of every session. It starts:

| # | What | Why |
|---|---|---|
| 1 | TG30 YDLidar driver | Publishes `/scan` (raw laser data) |
| 2 | Hardware driver | Controls wheels and motors |
| 3 | IMU filter (Madgwick) | Smooths the IMU → `/imu/imu_data` |
| 4 | EKF (wheel + IMU fusion) | Combines odom + IMU → `/odom` (smooth position) |
| 5 | URDF / TF publishers | Tells ROS the shape and layout of the robot |
| 6 | Joystick teleop | You can drive immediately with the stick |
| 7 | Scan cleanup pipeline | Creates `/scan_obstacles` (curb and grass edges included) |

```bash
roslaunch yahboomcar_nav laser_bringup.launch
```

**Yes — it brings up the IMU.** The IMU filter and EKF both start inside
`bringup.launch` which is called automatically by `laser_bringup.launch`.

**After running this, drive with the joystick to make sure the robot moves.**

---

## Does the Robot Use the IMU?

Yes, in three ways:

**Cartographer** — reads `/imu/imu_data` directly. When the robot turns,
the IMU gives Cartographer a good rotation estimate before the laser scan
even arrives. This makes the map much more accurate on outdoor terrain.

**EKF** — fuses wheel odometry + IMU into a smooth `/odom`. Even when
wheels slip on grass or a curb, the IMU keeps the position estimate steady.

**AMCL and pure pursuit** — use `/odom` as their motion model.
They benefit from IMU automatically through the EKF output.

---

## Does the Robot Use the Ackermann Bridge?

**No.** The ROSMASTER R2 hardware driver (`Mcnamu_driver.py`) does NOT
use `AckermannDriveStamped` messages. It subscribes to `/cmd_vel`
(standard Twist) but reads steering from `linear.y` instead of `angular.z`:

```
Driver expects:  msg.linear.x  = speed (m/s)
                 msg.linear.y  = steering angle (radians)   ← unusual!
                 msg.angular.z = ignored by firmware
```

The joystick already outputs `linear.y` natively. Pure pursuit outputs
standard `angular.z`, so `twist_to_rosmaster.py` converts it before
it reaches the driver.

---

## How the Joystick Works

The joystick is always active. No special setup needed.

```
Left stick  up/down        →  forward / reverse
Right stick left/right     →  steering
LB button (button 6)       →  HOLD to enable autonomous racing
Release LB                 →  instantly back to manual
```

The system uses a priority mixer (`twist_mux`):
```
Joystick teleop  (priority 90)  ←  always wins if you move the stick
Autonomous       (priority 50)  ←  only runs when LB held AND joystick idle
```

---

## Cartographer vs GMapping

**Use Cartographer.** Here is why it matters for a race course:

When you drive one full lap and return to where you started, Cartographer
sees that the current laser scan matches the beginning of the map and
**snaps the two ends together**. This is called loop closure. The whole
map gets re-adjusted so it is consistent everywhere.

GMapping does not do this. If you drive a full lap with GMapping, the start
and end of the map are usually off by 30 cm to 1 metre. AMCL then struggles
to locate the robot near the start of the lap.

---

## Step-by-Step Instructions

---

### Step 1 — Start the Car and LiDAR

Open a terminal on the robot:

```bash
roslaunch yahboomcar_nav laser_bringup.launch
```

Wait 5 seconds, then check that everything started:

```bash
# In a new terminal:
rostopic hz /scan          # should show ~7 Hz
rostopic hz /imu/imu_data  # should show ~50 Hz
rostopic hz /odom          # should show ~20 Hz
```

Drive with the joystick to confirm the wheels move.

---

### Step 2 — Build the Map

Open a new terminal:

```bash
roslaunch r2_tg30_race mapping_cartographer.launch
```

Open RViz to watch the map grow:

```bash
roslaunch r2_tg30_race view_mapping.launch
```

**Drive slowly around the full course** (about 0.2–0.3 m/s). Take at
least one complete lap.

#### Closing the Loop in Cartographer

When you return to where you started, **Cartographer closes the loop
automatically**. You will see the map "snap" into place in RViz. The
path line will reconnect cleanly to the start. Wait about 10 seconds
for this to settle.

Signs the loop closed:
- Map looks clean — no doubled walls or blurry edges
- The path line makes a clean circle back to the start

**Save the map after the loop closes:**

```bash
rosrun map_server map_saver -f $(rospack find r2_tg30_race)/maps/driveway_course
rosservice call /finish_trajectory 0
rosservice call /write_state \
  "{filename: '$(rospack find r2_tg30_race)/maps/driveway_course.pbstream'}"
```

Stop Cartographer (Ctrl-C in that terminal).

Files you now have:
```
r2_tg30_race/maps/driveway_course.pgm    ← map image
r2_tg30_race/maps/driveway_course.yaml   ← map settings
r2_tg30_race/maps/driveway_course.pbstream  ← Cartographer state
```

---

### Step 3 — Start Localization

The robot needs to know where it is on the saved map before you record
the race path.

```bash
roslaunch r2_tg30_race localization_amcl.launch
```

Open RViz:

```bash
roslaunch r2_tg30_race view_localization.launch
```

#### Set the Robot's Starting Position

When AMCL first starts, it does not know where on the map the robot is.
Tell it:

1. In RViz toolbar, click **2D Pose Estimate**
2. Click on the map **where the robot actually is**
3. Drag the arrow to show which direction the robot faces
4. Release — the red particle cloud should shrink to a tight cluster

If the cloud does not converge, drive the robot forward and back a little.
AMCL will figure it out from the scan.

**Check localization is working:**
```bash
rostopic echo /amcl_pose | head -20
# You should see x, y, z coordinates updating as you move
```

---

### Step 4 — Record the Race Path

With localization running, start the waypoint recorder:

```bash
rosrun r2_tg30_race record_waypoints_live.py \
    _spacing_m:=0.20 \
    _out_yaml:=$(rospack find r2_tg30_race)/waypoints/waypoints.yaml
```

In RViz you will see a **cyan line** growing as you drive — these are
waypoints being saved every 0.20 metres in real time.

**Drive the race line at race speed.** The path records exactly how you
drive it, so pick the line you want the robot to follow.

When you finish the lap, press **Ctrl-C** in the recorder terminal. The
file saves automatically.

**Check the file is correct:**

```bash
python3 -c "
import yaml
with open('$(rospack find r2_tg30_race)/waypoints/waypoints.yaml') as f:
    d = yaml.safe_load(f)
print('frame_id:', d['frame_id'])        # MUST say: map
print('waypoints:', len(d['waypoints'])) # should be > 50 for a typical course
print('first:', d['waypoints'][0])
print('last: ', d['waypoints'][-1])
"
```

**The frame_id MUST say `map`.** If it says `odom`, localization was not
running when you recorded. Stop, restart localization, and record again.

---

### Step 5 — Close the Loop

Your last waypoint is wherever you stopped — probably close to but not
exactly at the first waypoint. This step adds bridge waypoints between
them so the robot can race the circuit forever without jumping.

```bash
python3 $(rospack find r2_tg30_race)/scripts/close_loop.py \
    --in_yaml  $(rospack find r2_tg30_race)/waypoints/waypoints.yaml \
    --out_yaml $(rospack find r2_tg30_race)/waypoints/waypoints_closed.yaml \
    --spacing_m 0.20 \
    --close_thresh 2.0
```

**If you get a gap error:** the distance between your last and first
waypoint is more than 2 metres. Either drive the course again and stop
closer to the start, or use `--close_thresh 3.5` (or whatever the error
message tells you the gap is).

Optional — smooth the seam where the bridge connects (recommended if gap
is bigger than 0.5 m):

```bash
python3 ... --smooth_window 7
```

---

### Step 6 — Check the Path in RViz Before Racing

This step lets you look at the path before the robot drives itself.

With `laser_bringup.launch` and `localization_amcl.launch` already
running, publish the path without starting the racing stack:

```bash
rosrun r2_tg30_race waypoint_map_builder.py \
    _yaml_file:=$(rospack find r2_tg30_race)/waypoints/waypoints_closed.yaml
```

Open RViz:

```bash
roslaunch r2_tg30_race view_localization.launch
```

**What you should see:**
- **Yellow line** — the race path the robot will follow
- **Green spheres** — individual waypoints every 0.2 m
- **Red arrow** — the robot's current location
- **Red particle cloud** — AMCL confidence (tight = good)

**Checklist before racing:**
- [ ] Yellow path is smooth — no big jumps or missing sections
- [ ] The loop closes cleanly — path forms a complete circle
- [ ] AMCL red arrow is where the robot actually is
- [ ] Green obstacle dots (curbs/grass) appear at the course edges

---

### Step 7 — Race

Make sure these are already running in other terminals:
- `laser_bringup.launch`
- `localization_amcl.launch`

Start the racing stack:

```bash
roslaunch r2_tg30_race racing_stack.launch \
    waypoint_yaml:=$(rospack find r2_tg30_race)/waypoints/waypoints_closed.yaml
```

Open the racing RViz view:

```bash
roslaunch r2_tg30_race view_racing.launch
```

**To start autonomous racing:** hold the **LB button** on the joystick.

**To stop:** release LB. The robot stops immediately and waits for you.

**To override at any time:** just move the joystick. Teleop priority (90)
always beats autonomous priority (50).

---

## What You See in RViz During Racing

| Display | Color | What it means |
|---|---|---|
| Race Path | Yellow line | The waypoints pure pursuit follows |
| Lookahead Point | Orange sphere | Where pure pursuit is aiming right now |
| Obstacle Scan | Green dots | Curbs, grass edges, obstacles |
| AMCL Pose | Red arrow | Robot location estimate |
| AMCL Particles | Red cloud | Tight cluster = confident, spread out = lost |
| Waypoints | Green spheres | Each 0.2 m waypoint on the path |
| Driving Mode | Text | "AUTO" when LB held, "MANUAL" otherwise |

---

## How Obstacle Avoidance Works

The robot uses two controllers at the same time:

**Pure pursuit** — follows the recorded race line

**Follow the Gap (FTG)** — reacts instantly to obstacles using the laser

`steering_modifier.py` decides which one to use based on how close the
nearest obstacle is:

```
Obstacle farther than 1.6 m  →  pure pursuit only (race line)
Obstacle 1.1 m – 1.6 m       →  blend of both
Obstacle closer than 1.1 m   →  FTG takes over (reactive steering)
Obstacle closer than 0.4 m   →  hard stop
```

**Curbs and grass count as obstacles automatically** because the laser is
tilted 5 degrees downward. It sees the face of a kerb (which sticks up
~10 cm) at about 1.3 metres ahead — plenty of time to react.

---

## All Launch Files — Quick Reference

### Step 1 — Always run first

```bash
roslaunch yahboomcar_nav laser_bringup.launch
```
Starts: LiDAR driver, hardware driver, IMU, EKF, joystick, scan pipeline.

---

### Step 2 — Mapping

```bash
# Map the course:
roslaunch r2_tg30_race mapping_cartographer.launch

# Watch in RViz:
roslaunch r2_tg30_race view_mapping.launch

# Save the map when done:
rosrun map_server map_saver -f $(rospack find r2_tg30_race)/maps/driveway_course
```

`mapping_cartographer.launch` arguments:
```bash
imu_topic:=/imu/imu_data   # IMU source (default, correct)
resolution:=0.05           # map resolution in metres
```

---

### Step 3 — Localization

```bash
# Load the saved map and start AMCL:
roslaunch r2_tg30_race localization_amcl.launch

# Check localization in RViz:
roslaunch r2_tg30_race view_localization.launch
```

`localization_amcl.launch` arguments:
```bash
map_file:=/path/to/map.yaml   # which map to load (default: driveway_course.yaml)
```

---

### Step 4 — Race

```bash
# Start the racing stack:
roslaunch r2_tg30_race racing_stack.launch \
    waypoint_yaml:=$(rospack find r2_tg30_race)/waypoints/waypoints_closed.yaml

# Watch in RViz:
roslaunch r2_tg30_race view_racing.launch
```

`racing_stack.launch` arguments:
```bash
waypoint_yaml:=/path/to/waypoints_closed.yaml   # the path to follow
```

---

### Internal launch files (started automatically — you do not run these directly)

| File | Started by | What it does |
|---|---|---|
| `yahboomcar_bringup/launch/bringup.launch` | `laser_bringup.launch` | Driver, IMU, EKF, joystick, URDF |
| `yahboomcar_ctrl/launch/yahboom_joy.launch` | `bringup.launch` | Joystick node |
| `r2_tg30_race/launch/tg30_bringup.launch` | (superseded by laser_bringup) | LiDAR driver only |
| `r2_tg30_race/launch/scan_cleanup.launch` | `laser_bringup.launch` | Scan filter chain |

---

## Waypoints and Path — How It All Works

### What a waypoint is

A waypoint is a saved position on the map:
```yaml
- {x: 12.34, y: 5.67, yaw: 1.23}
```
- `x` and `y` are metres on the map (0,0 is the map origin)
- `yaw` is the direction the robot faced (radians: 0=east, 1.57=north)

### Why map frame matters

Map frame coordinates do not drift. If you recorded in odom frame, the
same physical spot might be at (3.0, 1.0) today and (2.7, 1.3) tomorrow
because odom resets on every boot. Map frame always means the same real
location because AMCL continuously corrects the map→odom transform.

### How recording works (record_waypoints_live.py)

Every 20 cm of real travel, the recorder asks TF: "where is `base_link`
in the `map` frame right now?" and saves that answer. It publishes
`/recorded_path_live` so you can watch the cyan line grow in RViz.
On Ctrl-C it writes the YAML file.

### How loop closure works (close_loop.py)

Measures the gap from last waypoint to first, then fills it with waypoints
spaced every 0.20 m. Heading is smoothly interpolated across the bridge.
Optional smoothing removes any kink at the join.

### How pure pursuit follows the path

1. Ask TF: "where is `base_link` in the `map` frame?"
2. Find the point on the path that is 0.65 m ahead of the robot
3. Calculate the angle to that point
4. Publish a Twist command with appropriate speed and angular.z
5. `twist_to_rosmaster.py` converts angular.z → linear.y for the driver
6. Repeat at 20 Hz

The orange sphere in RViz shows the lookahead point moving ahead of the
robot as it drives.

---

## Configuration Files

All in `r2_tg30_race/config/`:

### pure_pursuit.yaml — path following
```yaml
lookahead_distance: 0.65  # aim this far ahead (metres)
base_speed:         0.45  # normal speed (m/s)
max_speed:          0.70  # fastest allowed (m/s)
min_speed:          0.18  # slowest on tight turns (m/s)
max_angular_z:      1.40  # max steering rate (rad/s)
goal_tolerance:     0.30  # stop within this of last waypoint (m)
```

### follow_the_gap.yaml — obstacle avoidance
```yaml
danger_distance:   1.10   # start reacting at this distance (m)
stop_distance:     0.40   # hard stop if this close (m)
front_angle_deg:   120.0  # how wide to look for gaps (degrees)
gap_threshold:     0.70   # minimum gap to drive through (m)
max_speed:         0.40   # FTG max speed (m/s)
```

### steering_modifier.yaml — PP/FTG blend
```yaml
danger_distance:   1.10   # below this: use FTG only
blend_distance:    1.60   # between this and danger: blend PP+FTG
stop_distance:     0.45   # below this: hard stop
front_fov_deg:     110.0  # forward field of view for obstacle check
```

### pointcloud_to_laserscan.yaml — curb/grass detection
```yaml
min_height: 0.025  # ignore flat ground (below 2.5 cm above ground)
max_height: 0.280  # capture curbs and grass (up to 28 cm tall)
```
Curbs are ~10–15 cm tall. These settings make them appear in
`/scan_obstacles` so FTG and the maps treat them as obstacles.

### joystick_deadman.yaml — LB button index
```yaml
deadman_button_index: 5   # LB on Yahboom controller (Jetson mode)
```
Run `rostopic echo /joy` and press buttons to find the right index
for your controller.

---

## All Scripts

| Script | What it does |
|---|---|
| `record_waypoints_live.py` | Records waypoints every 0.2 m during joystick drive |
| `close_loop.py` | Bridges last waypoint to first for circuit racing |
| `waypoint_extractor.py` | Extracts waypoints from a saved rosbag (offline) |
| `waypoint_map_builder.py` | Publishes `/race_path` and `/race_waypoints` from YAML |
| `pure_pursuit_twist.py` | Follows the path using TF map→base_link |
| `follow_the_gap.py` | Reactive obstacle avoidance from laser scan |
| `steering_modifier.py` | Blends pure pursuit and FTG by obstacle distance |
| `twist_to_rosmaster.py` | Converts angular.z → linear.y for the R2 driver |
| `scan_to_cloud.py` | Converts LaserScan → PointCloud2 |
| `cmdvel_gate.py` | Passes auto commands only when LB is held |
| `joy_deadman.py` | Reads LB button, publishes /auto_enable |
| `mode_indicator.py` | Publishes "AUTO" or "MANUAL" for RViz |
| `bag_control_recorder.py` | Start/stop rosbag recording via service call |
| `twist_to_ackermann.py` | (Not used — kept for reference only) |

---

## Quick Command Reference

```bash
# ── Every session ──────────────────────────────────────────────
roslaunch yahboomcar_nav laser_bringup.launch          # ALWAYS FIRST

# ── Mapping session ────────────────────────────────────────────
roslaunch r2_tg30_race mapping_cartographer.launch
roslaunch r2_tg30_race view_mapping.launch
# drive the course, wait for loop closure, then:
rosrun map_server map_saver -f $(rospack find r2_tg30_race)/maps/driveway_course

# ── Record path (localization must be running) ─────────────────
roslaunch r2_tg30_race localization_amcl.launch
rosrun r2_tg30_race record_waypoints_live.py \
    _spacing_m:=0.20 \
    _out_yaml:=$(rospack find r2_tg30_race)/waypoints/waypoints.yaml
# drive the course, then Ctrl-C to save

# ── Close the loop ─────────────────────────────────────────────
python3 $(rospack find r2_tg30_race)/scripts/close_loop.py \
    --in_yaml  $(rospack find r2_tg30_race)/waypoints/waypoints.yaml \
    --out_yaml $(rospack find r2_tg30_race)/waypoints/waypoints_closed.yaml \
    --spacing_m 0.20 --close_thresh 2.0

# ── Race ───────────────────────────────────────────────────────
roslaunch r2_tg30_race localization_amcl.launch
roslaunch r2_tg30_race racing_stack.launch \
    waypoint_yaml:=$(rospack find r2_tg30_race)/waypoints/waypoints_closed.yaml
roslaunch r2_tg30_race view_racing.launch
# hold LB to race, release to stop
```

---

## Troubleshooting

| Problem | What to check |
|---|---|
| LiDAR not publishing | `ls /dev/ydlidar` — check USB connection |
| Joystick does nothing | `ls /dev/input/js0` — plug in joystick first |
| `/imu/imu_data` not publishing | Check `laser_bringup.launch` started without errors |
| `frame_id: odom` in waypoints.yaml | Localization was not running — redo Step 4 |
| Map looks blurry or doubled | Loop closure did not fire — drive slower, full lap |
| AMCL particles scattered | Use 2D Pose Estimate in RViz to set initial position |
| Gap error in close_loop.py | Stop closer to start, or increase `--close_thresh` |
| Robot steers wrong direction | Check `twist_to_rosmaster.py` is running (check rqt_graph) |
| Robot drives but doesn't steer | Pure pursuit angular.z not reaching driver — check topic chain |
| FTG fires too early | Increase `danger_distance` in follow_the_gap.yaml |
| Robot lost during race | Slow down; increase `min_particles` in localization_amcl.launch |
