#!/usr/bin/env python3

import argparse

import psutil
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import BatteryState


class LaptopBatteryMonitorNode(Node):
    def __init__(self, topic_name='laptop_battery', publish_interval=5.0):
        super().__init__('laptop_battery_monitor')

        self.publisher_ = self.create_publisher(BatteryState, topic_name, 10)
        self.timer = self.create_timer(publish_interval, self.timer_callback)
        self.get_logger().info(
            f"Laptop battery node started (topic={topic_name}, interval={publish_interval}s)."
        )

    def timer_callback(self):
        battery = psutil.sensors_battery()

        if battery is None:
            self.get_logger().warn_throttle(5.0, "Battery information not available.")
            return

        msg = BatteryState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "base_link"

        # ROS 2 expects percentage in a 0.0 to 1.0 range
        msg.percentage = float(battery.percent) / 100.0

        if battery.power_plugged:
            if battery.percent >= 100:
                msg.power_supply_status = BatteryState.POWER_SUPPLY_STATUS_FULL
            else:
                msg.power_supply_status = BatteryState.POWER_SUPPLY_STATUS_CHARGING
        else:
            msg.power_supply_status = BatteryState.POWER_SUPPLY_STATUS_DISCHARGING

        self.publisher_.publish(msg)
        self.get_logger().info(f"Battery percentage published: {msg.percentage}")


def main(args):
    rclpy.init(args=args.ros_args)
    node = LaptopBatteryMonitorNode(
        topic_name=args.topic_name,
        publish_interval=args.publish_interval,
    )

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Publish laptop battery state via ROS 2.")
    parser.add_argument(
        '--topic_name',
        default='laptop_battery',
        help='BatteryState topic name (default: laptop_battery)',
    )
    parser.add_argument(
        '--publish_interval',
        type=float,
        default=5.0,
        help='Publish interval in seconds (default: 5.0)',
    )
    parser.add_argument(
        '--ros_args',
        nargs=argparse.REMAINDER,
        help='Arguments passed to rclpy.init (e.g. --ros-args -p foo:=bar)',
    )
    args = parser.parse_args()
    main(args)
