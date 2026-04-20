#!/usr/bin/env bash

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="${WORKSPACE:-$SCRIPT_DIR}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/melodic/setup.bash}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-6}"
RUN_BUILD=1
MAP_FILE=""

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

ROSCORE_PID=""
LAUNCH_PID=""
LAUNCH_LOG=""
LOG_DIR=""

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Smoke-test this ROS Melodic workspace without requiring the real car or live LiDAR.

Options:
  --workspace PATH    Catkin workspace root. Default: script directory
  --ros-setup PATH    ROS setup.bash to source. Default: /opt/ros/melodic/setup.bash
  --map FILE          Saved map yaml for AMCL smoke test
  --skip-build        Skip catkin_make
  --timeout SEC       Seconds to wait before checking a live launch. Default: 6
  --help              Show this help

Examples:
  ./test_stack.sh
  ./test_stack.sh --map ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/maps/driveway_course.yaml
EOF
}

slugify() {
  echo "$1" | tr ' /:' '___'
}

info() {
  printf '[INFO] %s\n' "$*"
}

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf '[PASS] %s\n' "$*"
}

warn() {
  WARN_COUNT=$((WARN_COUNT + 1))
  printf '[WARN] %s\n' "$*"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf '[FAIL] %s\n' "$*"
}

cleanup_launch() {
  if [[ -n "${LAUNCH_PID}" ]] && kill -0 "${LAUNCH_PID}" 2>/dev/null; then
    kill "${LAUNCH_PID}" 2>/dev/null || true
    wait "${LAUNCH_PID}" 2>/dev/null || true
  fi
  LAUNCH_PID=""
  LAUNCH_LOG=""
}

cleanup_roscore() {
  cleanup_launch
  if [[ -n "${ROSCORE_PID}" ]] && kill -0 "${ROSCORE_PID}" 2>/dev/null; then
    kill "${ROSCORE_PID}" 2>/dev/null || true
    wait "${ROSCORE_PID}" 2>/dev/null || true
  fi
  ROSCORE_PID=""
}

cleanup_all() {
  cleanup_roscore
}

trap cleanup_all EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace)
      WORKSPACE="$2"
      shift 2
      ;;
    --ros-setup)
      ROS_SETUP="$2"
      shift 2
      ;;
    --map)
      MAP_FILE="$2"
      shift 2
      ;;
    --skip-build)
      RUN_BUILD=0
      shift
      ;;
    --timeout)
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ ! -d "$WORKSPACE/src" ]]; then
  echo "Workspace does not look like a catkin workspace: $WORKSPACE" >&2
  exit 2
fi

if [[ ! -f "$ROS_SETUP" ]]; then
  echo "ROS setup file not found: $ROS_SETUP" >&2
  exit 2
fi

source "$ROS_SETUP"

LOG_DIR="$WORKSPACE/test_logs/smoke_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

WAYPOINT_FILE="$WORKSPACE/src/r2_tg30_race/waypoints/waypoints.yaml"
DEFAULT_MAP_FILE="$WORKSPACE/src/r2_tg30_race/maps/driveway_course.yaml"
URDF_XACRO="$WORKSPACE/src/yahboomcar_description/urdf/yahboomcar_R2.urdf.xacro"

if [[ -z "$MAP_FILE" && -f "$DEFAULT_MAP_FILE" ]]; then
  MAP_FILE="$DEFAULT_MAP_FILE"
fi

run_cmd() {
  local name="$1"
  shift
  local stdout_file="$LOG_DIR/$(slugify "$name").out"
  local stderr_file="$LOG_DIR/$(slugify "$name").err"

  info "$name"
  if "$@" >"$stdout_file" 2>"$stderr_file"; then
    pass "$name"
    return 0
  fi

  fail "$name"
  if [[ -s "$stderr_file" ]]; then
    printf '        stderr: %s\n' "$stderr_file"
  fi
  return 1
}

check_launch_parse() {
  local name="$1"
  shift
  run_cmd "$name" roslaunch --nodes "$@"
}

start_roscore() {
  local roscore_log="$LOG_DIR/roscore.log"
  info "Starting roscore"
  roscore >"$roscore_log" 2>&1 &
  ROSCORE_PID=$!
  sleep 3

  if ! kill -0 "$ROSCORE_PID" 2>/dev/null; then
    fail "roscore failed to start"
    printf '        log: %s\n' "$roscore_log"
    return 1
  fi

  if ! rosnode list >/dev/null 2>&1; then
    fail "roscore started but ROS master is not responding"
    printf '        log: %s\n' "$roscore_log"
    return 1
  fi

  pass "roscore is up"
  return 0
}

start_launch() {
  local name="$1"
  shift

  cleanup_launch

  LAUNCH_LOG="$LOG_DIR/$(slugify "$name").log"
  info "Starting $name"
  roslaunch "$@" >"$LAUNCH_LOG" 2>&1 &
  LAUNCH_PID=$!
  sleep "$TIMEOUT_SECONDS"

  if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    fail "$name did not stay up for ${TIMEOUT_SECONDS}s"
    printf '        log: %s\n' "$LAUNCH_LOG"
    return 1
  fi

  pass "$name is still running"
  return 0
}

require_node() {
  local node_name="$1"
  if rosnode list 2>/dev/null | grep -Fx "$node_name" >/dev/null; then
    pass "Found node $node_name"
    return 0
  fi

  fail "Missing node $node_name"
  printf '        active nodes were written while %s was running\n' "$LAUNCH_LOG"
  rosnode list >"$LOG_DIR/active_nodes_$(date +%H%M%S).txt" 2>/dev/null || true
  return 1
}

require_param_equals() {
  local param_name="$1"
  local expected="$2"
  local actual

  if ! actual="$(rosparam get "$param_name" 2>/dev/null)"; then
    fail "Missing param $param_name"
    return 1
  fi

  if [[ "$actual" == "$expected" ]]; then
    pass "Param $param_name = $expected"
    return 0
  fi

  fail "Param $param_name expected $expected but got $actual"
  return 1
}

if (( RUN_BUILD )); then
  info "Building workspace with catkin_make"
  (
    cd "$WORKSPACE" &&
    catkin_make
  ) >"$LOG_DIR/catkin_make.out" 2>"$LOG_DIR/catkin_make.err"
  if [[ $? -eq 0 ]]; then
    pass "catkin_make"
  else
    fail "catkin_make"
  fi
else
  warn "Skipping catkin_make because --skip-build was used"
fi

if [[ -f "$WORKSPACE/devel/setup.bash" ]]; then
  source "$WORKSPACE/devel/setup.bash"
else
  warn "devel/setup.bash was not found. Continuing with only $ROS_SETUP sourced."
fi

if [[ ! -f "$URDF_XACRO" ]]; then
  fail "URDF xacro not found: $URDF_XACRO"
else
  run_cmd "URDF xacro expands" rosrun xacro xacro "$URDF_XACRO"
fi

check_launch_parse "Parse laser_bringup" yahboomcar_nav laser_bringup.launch
check_launch_parse "Parse tg30_bringup" r2_tg30_race tg30_bringup.launch start_driver:=false scan_topic:=/scan
check_launch_parse "Parse mapping_cartographer" r2_tg30_race mapping_cartographer.launch start_driver:=false scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles
check_launch_parse "Parse mapping_gmapping alias" r2_tg30_race mapping_gmapping.launch start_driver:=false scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles
check_launch_parse "Parse racing_stack" r2_tg30_race racing_stack.launch start_driver:=false scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles waypoint_yaml:="$WAYPOINT_FILE" use_ackermann_bridge:=true
check_launch_parse "Parse view_mapping" r2_tg30_race view_mapping.launch
check_launch_parse "Parse view_localization" r2_tg30_race view_localization.launch
check_launch_parse "Parse view_racing without overlay" r2_tg30_race view_racing.launch show_mode_indicator:=false

if [[ -n "$MAP_FILE" && -f "$MAP_FILE" ]]; then
  check_launch_parse "Parse localization_amcl" r2_tg30_race localization_amcl.launch start_driver:=false map_file:="$MAP_FILE" scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles
else
  warn "Skipping localization_amcl parse because no map yaml was found. Use --map FILE to enable it."
fi

if start_roscore; then
  if start_launch "Live mapping_cartographer" r2_tg30_race mapping_cartographer.launch start_driver:=false scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles; then
    require_node "/cartographer_node"
    require_node "/cartographer_occupancy_grid_node"
  fi
  cleanup_launch

  if start_launch "Live racing_stack" r2_tg30_race racing_stack.launch start_driver:=false scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles waypoint_yaml:="$WAYPOINT_FILE" use_ackermann_bridge:=true; then
    require_node "/waypoint_map_builder"
    require_node "/pure_pursuit_twist"
    require_node "/follow_the_gap"
    require_node "/joy_deadman"
    require_node "/cmdvel_gate"
    require_node "/steering_modifier"
    require_node "/twist_mux"
    require_node "/twist_to_ackermann"
    require_param_equals "/pure_pursuit_twist/lookahead_distance" "0.65"
    require_param_equals "/follow_the_gap/danger_distance" "1.1"
    require_param_equals "/steering_modifier/blend_distance" "1.6"
    require_param_equals "/twist_to_ackermann/wheelbase" "0.26"
  fi
  cleanup_launch

  if [[ -n "$MAP_FILE" && -f "$MAP_FILE" ]]; then
    if start_launch "Live localization_amcl" r2_tg30_race localization_amcl.launch start_driver:=false map_file:="$MAP_FILE" scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles; then
      require_node "/map_server"
      require_node "/amcl"
    fi
    cleanup_launch
  else
    warn "Skipping live localization_amcl because no map yaml was found."
  fi
fi

printf '\n'
printf 'Smoke test summary\n'
printf '  pass: %d\n' "$PASS_COUNT"
printf '  warn: %d\n' "$WARN_COUNT"
printf '  fail: %d\n' "$FAIL_COUNT"
printf '  logs: %s\n' "$LOG_DIR"

if (( FAIL_COUNT > 0 )); then
  exit 1
fi

exit 0
