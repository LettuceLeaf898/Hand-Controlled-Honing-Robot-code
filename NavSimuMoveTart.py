import turtle as t
import random

# ---------------- SCREEN SETUP ----------------
screen = t.Screen()
screen.setup(width=600, height=600)
screen.bgcolor("Dark blue")
screen.bgpic("chess.gif")
screen.title("Robot Target Chase - Equal Speed")
screen.tracer(0) 

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

# Set initial random destination
target.dest_x = random.randint(-250, 250)
target.dest_y = random.randint(-250, 250)

# ---------------- ROBOT ----------------
robot = t.Turtle()
screen.addshape("Zoomba2.gif")
robot.shape("circle")
robot.color("yellow")
robot.penup()
robot.shape("Zoomba2.gif")

# ---------------- SPEED CONSTANT ----------------
# Change this one number to speed up or slow down BOTH at once
GAME_SPEED = 2 

# ---------------- MAIN GAME LOOP ----------------
def game_loop():
    global targets_reached

    # 1. Target Movement
    target.setheading(target.towards(target.dest_x, target.dest_y))
    target.forward(GAME_SPEED) 

    # If target reaches its goal, pick a new one
    if target.distance(target.dest_x, target.dest_y) < 10:
        target.dest_x = random.randint(-250, 250)
        target.dest_y = random.randint(-250, 250)

    # 2. Robot Movement (Following the target)
    robot.setheading(robot.towards(target.pos()))
    robot.forward(GAME_SPEED)

    # 3. Check for "Tag" (Collision)
    # Using a slightly larger distance (20) so they can actually touch
    if robot.distance(target) < 20:
        targets_reached += 1
        update_score()
        # Move target to a brand new random spot to start the chase over
        target.goto(random.randint(-250, 250), random.randint(-250, 250))
        target.dest_x = random.randint(-250, 250)
        target.dest_y = random.randint(-250, 250)

    screen.update()
    screen.ontimer(game_loop, 20)

# ---------------- START ----------------
update_score()
game_loop()

screen.mainloop()