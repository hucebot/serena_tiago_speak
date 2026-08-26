#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import subprocess
import os

class RobotSpeaker(Node):
    def __init__(self):
        super().__init__('robot_speaker')

        # 1. Declare parameters (with default values)
        self.declare_parameter('speak_flag', 1)
        self.declare_parameter('action_topic', '/orchestrator/ui/current_task')
        self.declare_parameter('voice_type', 'kal_diphone') 
        self.declare_parameter('phrases_file', 'phrases.txt')

        # 2. Retrieve parameters
        self.speak_flag = self.get_parameter('speak_flag').value
        self.action_topic = self.get_parameter('action_topic').value
        self.voice_type = self.get_parameter('voice_type').value
        self.phrases_file = self.get_parameter('phrases_file').value

        # 3. Load phrases from the provided text file
        self.phrases = {}
        self.load_phrases()

        # 4. State variable to ensure we only speak once per action
        self.last_action = None

        # 5. Set up the Subscriber
        self.subscription = self.create_subscription(
            String,
            self.action_topic,
            self.action_callback,
            10
        )
        
        self.get_logger().info(f"Robot Speaker initialized.")
        self.get_logger().info(f"Topic: {self.action_topic}, Voice: {self.voice_type}, Speak Flag: {self.speak_flag}")

    def load_phrases(self):
        """Reads the text file containing 'action,phrase' pairs."""
        if not os.path.exists(self.phrases_file):
            self.get_logger().error(f"Phrases file not found at: {self.phrases_file}")
            return

        with open(self.phrases_file, 'r') as f:
            for line in f:
                # Ignore empty lines or comments
                if not line.strip() or line.startswith('#'):
                    continue
                
                # We expect the format: action_name, The phrase the robot should say
                parts = line.strip().split(',', 1)
                if len(parts) == 2:
                    action = parts[0].strip()
                    phrase = parts[1].strip()
                    self.phrases[action] = phrase
                    
        self.get_logger().info(f"Successfully loaded {len(self.phrases)} phrases.")

    def action_callback(self, msg):
        """Callback triggered when a new action is published to the topic."""
        current_action = msg.data

        # Ensure the phrase is only said once per action occurrence
        if current_action != self.last_action:
            self.last_action = current_action

            # Check if speech is enabled and if we have a phrase for this action
            if self.speak_flag == 1 and current_action in self.phrases:
                phrase = self.phrases[current_action]
                self.get_logger().info(f"Speaking: '{phrase}'")
                self.speak(phrase)

    def speak(self, phrase):
        """Uses Festival TTS to speak the given phrase."""
        # Escape double quotes to prevent breaking the command line string
        safe_phrase = phrase.replace('"', '\\"')

        # Construct the festival batch command
        # Syntax: festival -b '(voice_kal_diphone)' '(SayText "Hello")'
        cmd = [
            'festival',
            '-b',
            f'(voice_{self.voice_type})',
            f'(SayText "{safe_phrase}")'
        ]

        try:
            # Popen is used so the ROS 2 node doesn't block while the robot is speaking
            subprocess.Popen(cmd)
            print(f"Running Festival command: {cmd}")
   
        except FileNotFoundError:
            self.get_logger().error("Festival TTS is not installed. Please install it using 'sudo apt install festival'")
        except Exception as e:
            self.get_logger().error(f"Failed to execute Festival TTS: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = RobotSpeaker()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()