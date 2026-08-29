#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
from audio_common_msgs.msg import AudioData
from rcl_interfaces.msg import SetParametersResult
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, qos_profile_sensor_data
import numpy as np
import torch
import os
from pocket_tts import TTSModel

class KyutaiRobotSpeaker(Node):
    def __init__(self):
        super().__init__('kyutai_robot_speaker')

        # 1. Load the Pocket TTS model
        self.get_logger().info('Loading Kyutai Pocket TTS model...')
        self.model = TTSModel.load_model(language="english")

        # 2. Declare parameters
        self.declare_parameter('speak_flag', 1)
        self.declare_parameter('action_topic', '/orchestrator/ui/current_task')
        self.declare_parameter('voice', 'alba')
        self.declare_parameter('phrases_file', 'assets/phrases.txt')

        self.speak_flag = self.get_parameter('speak_flag').value
        self.action_topic = self.get_parameter('action_topic').value
        self.phrases_file = self.get_parameter('phrases_file').value
        initial_voice = self.get_parameter('voice').value

        # 3. Load initial voice
        try:
            self.voice_state = self.model.get_state_for_audio_prompt(initial_voice)
            self.get_logger().info(f'Loaded default voice: {initial_voice}')
        except Exception as e:
            self.get_logger().error(f'Failed to load voice "{initial_voice}": {e}')
            self.voice_state = self.model.get_state_for_audio_prompt("alba")

        self.add_on_set_parameters_callback(self.on_parameter_change)

        # 4. Load phrases
        self.phrases = {}
        self.load_phrases()
        self.last_action = None
        self.action_hist = []
        # 5. Pub/Sub Setup
        self.subscription = self.create_subscription(
            String,
            self.action_topic,
            self.action_callback,
            10
        )

        qos_state = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )

        self.subscription = self.create_subscription(
            String,
            '/serena_tts/text',
            self.error_callback,
            qos_state,
        )

        self.audio_pub = self.create_publisher(
            AudioData,
            '/audio_out/raw',
            10
        )

        self.get_logger().info('Kyutai Robot Speaker initialized and ready.')


    def error_callback(self, msg):
        """Callback for error messages."""
        if msg.data:
            self.speak(msg.data)

    def load_phrases(self):
        """Reads the text file containing 'action,phrase' pairs."""
        if not os.path.exists(self.phrases_file):
            self.get_logger().error(f"Phrases file not found at: {self.phrases_file}")
            return

        with open(self.phrases_file, 'r') as f:
            for line in f:
                if not line.strip() or line.startswith('#'):
                    continue
                parts = line.strip().split(',', 1)
                if len(parts) == 2:
                    self.phrases[parts[0].strip()] = parts[1].strip()

        self.get_logger().info(f"Successfully loaded {len(self.phrases)} phrases.")

    def on_parameter_change(self, params):
        for param in params:
            if param.name == 'voice':
                try:
                    self.voice_state = self.model.get_state_for_audio_prompt(param.value)
                    self.get_logger().info(f'Voice changed to: "{param.value}"')
                except Exception as e:
                    self.get_logger().error(f'Voice change failed: {e}')
                    return SetParametersResult(successful=False, reason=str(e))
            elif param.name == 'speak_flag':
                self.speak_flag = param.value
        return SetParametersResult(successful=True)

    def action_callback(self, msg):
        """Callback triggered when a new action is published."""
        current_action = msg.data
        self.action_hist.append(current_action)

        if current_action != self.last_action:
            self.last_action = current_action
            try:
                if self.speak_flag == 1 and current_action in self.phrases:
                    if current_action not in self.action_hist:
                        phrase = self.phrases[current_action]
                    else:
                         phrase = self.phrases.get(current_action+"2")
                    self.get_logger().info(f"Speaking: '{phrase}'")
                    self.speak(phrase)
            except Exception as e:
                self.get_logger().error(f"Error during action callback: {e}")

    def speak(self, phrase):
        """Generates audio stream with Kyutai and publishes raw bytes."""
        try:
            for chunk_tensor in self.model.generate_audio_stream(self.voice_state, phrase):

                # Convert float32 tensor chunk to 16-bit PCM numpy array
                audio_np = chunk_tensor.numpy()
                audio_int16 = (audio_np * 32767).astype(np.int16)

                # Convert to raw bytes and publish
                audio_msg = AudioData()
                audio_msg.data = list(audio_int16.tobytes())
                self.audio_pub.publish(audio_msg)

        except Exception as e:
            self.get_logger().error(f'Failed to stream TTS: {str(e)}')

def main(args=None):
    rclpy.init(args=args)
    node = KyutaiRobotSpeaker()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()