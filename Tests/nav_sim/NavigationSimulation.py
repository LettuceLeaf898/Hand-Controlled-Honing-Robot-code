import turtle as t
import random

# ---------------- SCREEN SETUP ----------------
screen = t.Screen()
screen.setup(width=600, height=600)
screen.bgcolor("light blue")
screen.title("Robot Target Chase")

# ---------------- SCORE DISPLAY ----------------
score_display = t.Turtle()
score_display.hideturtle()
score_display.penup()
score_display.goto(-280, 260)

targets_reached = 0

def update_score():
    score_display.clear()
    score_display.write(
        f"Targets Reached: {targets_reached}",
        font=("Arial", 16, "bold")
    )

# ---------------- TARGET ----------------
target = t.Turtle()
target.shape("circle")
target.color("red")
target.penup()

def move_target():
    x = random.randint(-250, 250)
    y = random.randint(-250, 250)
    target.goto(x, y)
    


# ---------------- ROBOT ----------------
robot = t.Turtle()
robot.shape("square")
robot.color("yellow")
robot.penup()
robot.speed(0)

# ---------------- MOVEMENT LOGIC ----------------
def move_robot():
    global targets_reached

    # Point robot toward the target
    robot.setheading(robot.towards(target.pos()))

    # Move robot forward
    robot.forward(5)

    # Check if robot reached the target
    if robot.distance(target) < 10:
        targets_reached += 1
        update_score()
        move_target()

    # Repeat movement
    screen.ontimer(move_robot, 40)

# ---------------- START GAME ----------------
# update_score()
# move_target()
# move_robot()

# screen.mainloop()