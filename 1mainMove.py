from move import move
from turn import turn  # Updated import to use the new function
from pololu_3pi_2040_robot import robot
import time


# Initialize hardware
display = robot.Display()
motors = robot.Motors()

def main():
    """
    Main control script for the robot.
    Demonstrates movement and turning in a sequence.
    """
    wheel_base = 9.1  # Distance between wheels in cm
    dowel_to_center = 5.25  # Distance from dowel to center of robot in cm
    front_back_base = 8.4
   
    # forwards: (distance, "move")
    # backwards: (-distance, "move")
    # turn left: (angle, "turn")  # positive angle
    # turn right: (-angle, "turn")  # negative angle

    # Movement and turning sequence

    sequence = [
        ((25 + dowel_to_center), "move"),
        (-90, "turn"),
        (50, "move"),
        (90, "turn"),
        (100, "move"),
        (-90, "turn"),
        (100, "move")
        # (90, "turn"),
        # (50, "move"),
        # (-50, "move"),
        # (90, "turn"),
        # (50, "move"),
        # (-90, "turn"),
        # (50, "move"),
        # (90, "turn"),
        # (100, "move"),
        # (90, "turn"),
        # (100, "move"),
        # (-100, "move"),
        # (-90, "turn"),
        # (50, "move"),
        # (-150, "move"),
        # (90, "turn"),
        # (150, "move"),
        # (90, "turn"),
        # (50, "move"),
        # (90, "turn"),
        # (50, "move"),
        # (-50, "move"),
        # (90, "turn"),
        # (50, "move"),
        # (-90, "turn"),
        # (150, "move"),
        # (90, "turn"),
        # (143, "move"),
        # (90, "turn"),
        # (103.5 - dowel_to_center, "move")
    ]

    # Total time for all actions
    move_time = 15 #75.5 + 1.6
    
    move_time -= ((len(sequence) - 1) * 0.25)  # Account for 0.35s wait time

    # Calculate total splits and time per split
    num_turns = sum(1 for step in sequence if step[-1] == "turn")
    num_move = sum(1 for step in sequence if step[-1] == "move")

    move_time = move_time - (num_turns * 0.36)  # Subtract time for turns

    total_distance = sum(abs(step[0]) for step in sequence if step[-1] == "move")

    if num_move > 0:
        time_per_cm = move_time / total_distance

    start_time = time.ticks_ms()

    # Execute the sequence
    for i, step in enumerate(sequence):
        curr_time = time.ticks_ms()
        time_offset = 0
        if step[-1] == "move":
            distance = step[0]
            action_time = abs(distance) * time_per_cm

            display_status(f"Move: {distance}cm", f"Time: {action_time:.2f}s")
            move(distance, action_time, stop_motors=False)
            time_offset = action_time - time.ticks_diff(curr_time, time.ticks_ms())

        elif step[-1] == "turn":
            angle = step[0]  # Just take the angle value
            display_status(f"Turn: {angle}°", "Turning...")
            turn(angle)  # Call turn with just the angle
            time_offset = 0.36 - time.ticks_diff(curr_time, time.ticks_ms())

        time.sleep(0.25)
        # Pause briefly between actions if not the last
    # end time
    end_time = time.ticks_ms()

    # display total time
    display.fill(0)
    display.text(f"time: {(time.ticks_diff(end_time, start_time) / 1000)-0.35:.4f}s", 0, 0)
    display.show()

def calculate_splits(distance_cm, is_turn=False):
    """ 
    Calculate the number of splits for a movement or turn.
    """
    if is_turn:
        return 0.80  # Fixed turn time corresponds to a split of 0.85
    else:
        return (abs(distance_cm) / 50.0)  # Round to nearest 50 cm

def display_status(line1, line2):
    """
    Display status messages on the robot's screen.
    """
    display.fill(0)
    display.text(line1, 0, 0)
    display.text(line2, 0, 10)
    display.show()

while True:
    if robot.ButtonA().is_pressed():
        display_status("Starting robot", "Initializing...")
        time.sleep(0.5)  # Delay to ensure initialization
        main()






# import time
# from move import move
# from turn import turn_with_trapezoid
# from shitTurn import turn_in_place
# from pololu_3pi_2040_robot import robot

# # Initialize hardware
# display = robot.Display()
# motors = robot.Motors()

# def main():
#     """
#     Main control script for the robot.
#     Demonstrates movement and turning in a sequence.
#     """
#     # Total time for all actions
#     move_time = 13.0

#     # Movement and turning sequence
#     sequence = [
#         (30, "move"),  
#         (-90, "turn"),  
#         (30, "move"),  
#         (90, "turn"),
#         (30, "move"),
#         (90, "turn"),
#         (30, "move"),
#         (90, "turn"),
#         (60, "move"),
#         (90, "turn"),
#         (0.5, "move")
#     ]

#     # Calculate total splits and time per split
#     total_splits = sum(
#         calculate_splits(value, is_turn=(action == "turn")) for value, action in sequence
#     )
#     time_per_split = move_time / total_splits

#     # Execute the sequence
#     for i, (value, action) in enumerate(sequence):
#         splits = calculate_splits(value, is_turn=(action == "turn"))
#         action_time = time_per_split * splits

#         # Check if this is the last move/turn
#         is_last_action = i == len(sequence) - 1

#         if action == "move":
#             display_status(f"Move: {value}cm", f"Time: {action_time:.2f}s")
#             move(value, action_time, stop_motors=is_last_action)
#         elif action == "turn":
#             display_status(f"Turn: {value}°", f"Time: {action_time:.2f}s")
#             #turn_with_trapezoid(value, action_time, stop_motors=is_last_action)
#             turn_in_place(value)

#         time.sleep(0.75)
#         # Pause briefly between actions if not the last
#         # if not is_last_action:
#         #     time.sleep(0.5)

# def calculate_splits(distance_cm, is_turn=False):
#     """ 
#     Calculate the number of splits for a movement or turn.
#     """
#     if is_turn:
#         return 0.45  # Turns always take 0.75 split
#     else:
#         return (abs(distance_cm) / 50)  # Round to nearest 50 cm

# def display_status(line1, line2):
#     """
#     Display status messages on the robot's screen.
#     """
#     display.fill(0)
#     display.text(line1, 0, 0)
#     display.text(line2, 0, 10)
#     display.show()

# while True:
#     if robot.ButtonA().is_pressed():
#         display_status("Starting robot", "Initializing...")
#         time.sleep(0.5)  # Delay to ensure initialization
#         main()