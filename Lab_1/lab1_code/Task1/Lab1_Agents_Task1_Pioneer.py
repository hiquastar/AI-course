# Make sure to have the server side running in V-REP:
# in a child script of a V-REP scene, add following command
# to be executed just once, at simulation start:
#
# simExtRemoteApiStart(19999)
# then start simulation, and run this program.
#
# IMPORTANT: for each successful call to simxStart, there
# should be a corresponding call to simxFinish at the end!
import Lab1_Agents_Task1_World as World
import random
import math


SPEED = 3.0         # wheel speed when driving forward
TURN_SPEED = 1.0    # wheel speed when turning on the spot
WALL_DIST = 0.5     # m: wall closer than this -> turn away from it
DANGER_DIST = 0.2   # m: wall closer than this -> back up



# --- 1a. Random agent: random actions, ignores sensor input ---

randomSpeed = dict(speedLeft=0, speedRight=0)
randomUntil = 0

def random_agent(simulationTime, left, right, energy):
    global randomSpeed, randomUntil
    # new random speeds every 0.5 - 1.5 s
    if simulationTime >= randomUntil:
        randomSpeed = dict(speedLeft=random.uniform(-SPEED, SPEED),
                           speedRight=random.uniform(-SPEED, SPEED))
        randomUntil = simulationTime + random.randint(500, 1500)
    return randomSpeed



# --- 1b. Fixed agent: same sequence of actions, ignores sensor input ---

# (duration in ms, wheel speeds)
fixedSequence = [
    (4000, dict(speedLeft=SPEED, speedRight=SPEED)),             # forward
    (1000, dict(speedLeft=TURN_SPEED, speedRight=-TURN_SPEED)),  # turn right
    (3000, dict(speedLeft=SPEED, speedRight=SPEED)),             # forward
    (1000, dict(speedLeft=-TURN_SPEED, speedRight=TURN_SPEED)),  # turn left
]

def fixed_agent(simulationTime, left, right, energy):
    # only the time picks the action, and the list repeats
    cycleTime = sum(duration for duration, speed in fixedSequence)
    t = simulationTime % cycleTime
    for duration, speed in fixedSequence:
        if t < duration:
            return speed
        t -= duration





# --- Helper: avoid walls ---
# Gives speeds that move away from a wall, or None if no wall is close.

def avoid_walls(left, right):
    # 1. too close: back up, away from the nearer wall
    if left < DANGER_DIST or right < DANGER_DIST:
        if left < right:   # nearer on the left -> turn right
            return dict(speedLeft=-0.5, speedRight=-TURN_SPEED)
        else:              # nearer on the right -> turn left
            return dict(speedLeft=-TURN_SPEED, speedRight=-0.5)
    # 2. wall ahead: turn on the spot to the side with more room
    if left < WALL_DIST and right < WALL_DIST:
        if left > right:   # more room on the left
            return dict(speedLeft=-TURN_SPEED, speedRight=TURN_SPEED)
        else:              # more room on the right
            return dict(speedLeft=TURN_SPEED, speedRight=-TURN_SPEED)
    # 3. wall on one side: turn away from it
    if left < WALL_DIST:
        return dict(speedLeft=SPEED, speedRight=-0.5)   # turn right
    if right < WALL_DIST:
        return dict(speedLeft=-0.5, speedRight=SPEED)   # turn left
    # 4. no wall close
    return None

# --- Helper: drive to the nearest block ---
# energy.direction > 0: block is on the right

def go_to_block(energy):
    if energy.direction > 0.4:
        return dict(speedLeft=SPEED, speedRight=SPEED * 0.1)
    if energy.direction > 0.1:
        return dict(speedLeft=SPEED, speedRight=SPEED * 0.6)
    if energy.direction < -0.4:
        return dict(speedLeft=SPEED * 0.1, speedRight=SPEED)
    if energy.direction < -0.1:
        return dict(speedLeft=SPEED * 0.6, speedRight=SPEED)
    return dict(speedLeft=SPEED, speedRight=SPEED)


# --- Helper: follow the wall on the left (memory agent) ---
# Only the left sensor can see a wall at the side, so we keep the wall on the left.
# wallLostFor: ms since the left sensor last saw the wall.

FOLLOW_NEAR = 0.4   # m: wall closer than this -> steer away from it
FOLLOW_FAR  = 0.7   # m: wall farther than this -> wall is lost
CORNER_TIME = 1500  # ms: wall lost shorter than this -> a corner, turn left

def follow_wall(left, right, wallLostFor):
    # too close: back up
    if left < DANGER_DIST or right < DANGER_DIST:
        return avoid_walls(left, right)
    # wall ahead: turn right, so the wall is on the left
    if right < WALL_DIST:
        return dict(speedLeft=TURN_SPEED, speedRight=-TURN_SPEED)
    # too close to the wall: steer right
    if left < FOLLOW_NEAR:
        return dict(speedLeft=SPEED, speedRight=SPEED * 0.6)
    # good distance: go straight
    if left <= FOLLOW_FAR:
        return dict(speedLeft=SPEED, speedRight=SPEED)
    # wall just ended: turn left around the corner
    if wallLostFor < CORNER_TIME:
        return dict(speedLeft=SPEED * 0.5, speedRight=SPEED)
    # no wall for a while: go straight until we find one
    return dict(speedLeft=SPEED, speedRight=SPEED)



# --- 1c. Reflex agent: uses only what it sees now ---
# Avoid walls first, then drive to the nearest block.

def reflex_agent(simulationTime, left, right, energy):
    avoidSpeed = avoid_walls(left, right)
    if avoidSpeed is not None:
        return avoidSpeed
    return go_to_block(energy)


# --- 1d. Agent with memory ---
# Default strategy: act like the reflex agent.
# Not closer to the block for TIMEOUT ms -> stuck -> follow the wall (Figure 2).
# Go back when closer than ever before, or when wall following takes too long.
# Stuck again on the same block -> follow the wall longer.

TIMEOUT = 5000          # ms: not closer to the block for this long -> stuck
FOLLOW_TIME = 8000      # ms: wall following time, x the number of times stuck
MAX_STUCK_COUNT = 4     # so wall following is at most 32 s
LEAVE_MARGIN = 0.1      # m: this much closer than before -> stop following

memory = dict(collected       = 0,             # blocks collected at the last check
              closestDistance = float('inf'),  # closest we got to the block
              lastCloserTime  = 0,             # when we last got closer to the block
              mode            = "goToBlock",   # "goToBlock" or "followWall"
              followEndTime   = 0,             # when to stop wall following
              lastWallTime    = 0,             # when the left sensor last saw the wall
              stuckCount      = 0)             # times stuck on this block

def memory_agent(simulationTime, left, right, energy):
    # new block collected: forget the old one
    if blocksCollected > memory["collected"]:
        memory["collected"] = blocksCollected
        memory["closestDistance"] = float('inf')
        memory["lastCloserTime"] = simulationTime
        memory["mode"] = "goToBlock"
        memory["stuckCount"] = 0

    # --- alternative strategy: follow the wall ---
    if memory["mode"] == "followWall":
        if energy.distance < memory["closestDistance"] - LEAVE_MARGIN:
            print("Got around the wall, going to the block again")
            memory["mode"] = "goToBlock"
            memory["closestDistance"] = energy.distance
            memory["lastCloserTime"] = simulationTime
        elif simulationTime > memory["followEndTime"]:
            print("Wall following took too long, going to the block again")
            memory["mode"] = "goToBlock"
            memory["lastCloserTime"] = simulationTime
        else:
            if left <= FOLLOW_FAR:      # wall is still there
                memory["lastWallTime"] = simulationTime
            wallLostFor = simulationTime - memory["lastWallTime"]
            return follow_wall(left, right, wallLostFor)

    # --- default strategy: like the reflex agent ---
    # got closer: remember it
    if energy.distance < memory["closestDistance"] - 0.05:
        memory["closestDistance"] = energy.distance
        memory["lastCloserTime"] = simulationTime

    # not closer for too long: stuck, so follow the wall
    if simulationTime - memory["lastCloserTime"] > TIMEOUT:
        memory["stuckCount"] = min(memory["stuckCount"] + 1, MAX_STUCK_COUNT)
        memory["followEndTime"] = simulationTime + FOLLOW_TIME * memory["stuckCount"]
        memory["lastWallTime"] = simulationTime
        memory["mode"] = "followWall"
        print("Stuck", memory["stuckCount"], "time(s), following the wall on the left")
        return follow_wall(left, right, 0)

    return reflex_agent(simulationTime, left, right, energy)



# --- Performance measures (Q3) ---

RUN_TIME = 300000
path = []

def save_position(simulationTime, motorSpeed):
    if path and simulationTime - path[-1][0] < 200:
        return
    _, pos = World.vrep.simxGetObjectPosition(robot.clientID, 
                                              robot.pioneerRobotHandle, -1, 
                                              World.vrep.simx_opmode_oneshot_wait)
    path.append((simulationTime, pos[0], pos[1], motorSpeed['speedLeft'], motorSpeed['speedRight']))

def count_crashes():
    crashes = 0
    wasStuck = False
    for i in range(5, len(path)):
        t0, x0, y0, _, _ = path[i - 5]
        t, x, y, sl, sr = path[i]
        realSpeed = math.hypot(x - x0, y - y0) / ((t - t0) / 1000)
        wheelSpeed = abs(0.1 * (sl + sr) / 2)
        stuck = sl * sr > 0 and wheelSpeed > 0.1 and realSpeed < 0.2 * wheelSpeed
        if stuck and not wasStuck:
            crashes += 1
        wasStuck = stuck
    return crashes

def explored_area():
    squares = {(math.floor(x / 0.5), math.floor(y / 0.5)) for _, x, y, _, _ in path}
    return len(squares) * 0.25



# --- Main ---

# choose the agent: "random", "fixed", "reflex" or "memory"
AGENT = "memory"
agents = dict(random=random_agent, fixed=fixed_agent,
              reflex=reflex_agent, memory=memory_agent)
agent = agents[AGENT]
blocksCollected = 0

# connect to the server
robot = World.init()
# print important parts of the robot
print(sorted(robot.keys()))
print("Agent:", AGENT)

while robot: # main Control loop
    # --- Perception Phase: Get information about environment ---
    simulationTime = World.getSimulationTime()
    left = World.getSensorReading("ultraSonicSensorLeft")
    right = World.getSensorReading("ultraSonicSensorRight")
    energy = World.getSensorReading("energySensor")
    if simulationTime%1000==0:
        # print some useful info, but not too often
        print ('Time:',simulationTime,\
               'ultraSonicSensorLeft:',left,\
               "ultraSonicSensorRight:", right)

    # collected blocks are moved to (1000, 1000),
    # so a block this far away means all are collected
    if energy.distance > 100:
        print("All blocks collected!")
        World.STOP()
        break
    if simulationTime > RUN_TIME:
        print("5 minutes are over")
        World.STOP()
        break

    # --- Reasoning: figure out which action to take ---
    motorSpeed = agent(simulationTime, left, right, energy)

    # --- Action Phase: Assign speed to wheels ---
    # assign speed to the wheels
    World.setMotorSpeeds(motorSpeed)
    save_position(simulationTime, motorSpeed)
    # try to collect the block (works within 0.5 m).
    # Only try when it is close, because each call is slow.
    if energy.distance < 0.8 and World.collectNearestBlock() == 'Energy collected :)':
        blocksCollected += 1
        print("Energy collected! Blocks collected:", blocksCollected)

# --- Results for Table 1 (Q3) ---
print("Agent:", AGENT)
print("Measure 1, blocks collected:", blocksCollected)
print("Measure 2, crashes:", count_crashes())
print("Measure 3, area explored (m2):", explored_area())
