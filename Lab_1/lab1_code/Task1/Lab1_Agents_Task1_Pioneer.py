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

# choose the agent: "random", "fixed", "reflex" or "memory"
AGENT = "reflex"

SPEED = 2.0         # forward wheel speed
TURN_SPEED = 1.0   # wheel speed when turning on the spot
WALL_DIST = 0.5     # a wall closer than this is "too close"
DANGER_DIST = 0.2   # a wall closer than this: back up before turning


##########################################################
# 1a. Random agent: random actions, ignores sensor input #
##########################################################
randomSpeed = dict(speedLeft=0, speedRight=0)
randomUntil = 0

def random_agent(simulationTime, left, right, energy):
    global randomSpeed, randomUntil
    # pick a new random action, and keep it for a random time (0.5 - 1.5 s)
    if simulationTime >= randomUntil:
        randomSpeed = dict(speedLeft=random.uniform(-SPEED, SPEED),
                           speedRight=random.uniform(-SPEED, SPEED))
        randomUntil = simulationTime + random.randint(500, 1500)
    return randomSpeed


###################################################################
# 1b. Fixed agent: same sequence of actions, ignores sensor input #
###################################################################
# (duration in ms, wheel speeds)
fixedSequence = [
    (4000, dict(speedLeft=SPEED, speedRight=SPEED)),             # forward
    (1000, dict(speedLeft=TURN_SPEED, speedRight=-TURN_SPEED)),  # turn right
    (3000, dict(speedLeft=SPEED, speedRight=SPEED)),             # forward
    (1000, dict(speedLeft=-TURN_SPEED, speedRight=TURN_SPEED)),  # turn left
]

def fixed_agent(simulationTime, left, right, energy):
    # the action only depends on the time, so the sequence repeats forever
    cycleTime = sum(duration for duration, speed in fixedSequence)
    t = simulationTime % cycleTime
    for duration, speed in fixedSequence:
        if t < duration:
            return speed
        t -= duration


##################################################################
# Helper: wall avoidance (used by the reflex and memory agents)  #
# Only looks at the current sensor readings.                     #
# Returns wheel speeds that move away from a wall,               #
# or None when no wall is close (then another rule decides).     #
##################################################################
def avoid_walls(left, right):
    # 1. wall very close -> back up, turning away from the closer side
    if left < DANGER_DIST or right < DANGER_DIST:
        if left < right:   # closer on the left -> back up, nose turns right
            return dict(speedLeft=-0.5, speedRight=-TURN_SPEED)
        else:              # closer on the right -> back up, nose turns left
            return dict(speedLeft=-TURN_SPEED, speedRight=-0.5)
    # 2. wall in front (both sensors) -> turn on the spot towards the free side
    if left < WALL_DIST and right < WALL_DIST:
        if left > right:   # more space on the left -> turn left
            return dict(speedLeft=-TURN_SPEED, speedRight=TURN_SPEED)
        else:              # more space on the right -> turn right
            return dict(speedLeft=TURN_SPEED, speedRight=-TURN_SPEED)
    # 3. wall on one side -> curve away from it
    if left < WALL_DIST:
        return dict(speedLeft=SPEED, speedRight=-0.5)   # turn right
    if right < WALL_DIST:
        return dict(speedLeft=-0.5, speedRight=SPEED)   # turn left
    # 4. no wall close
    return None


###############################################################
# Helper: drive towards the nearest block                    #
# energy.direction > 0: block is on the right                #
###############################################################
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


###############################################################
# 1c. Reflex agent: only uses the current sensor readings     #
# first avoid walls, then drive towards the nearest block     #
###############################################################
def reflex_agent(simulationTime, left, right, energy):
    wallAction = avoid_walls(left, right)
    if wallAction is not None:
        return wallAction
    return go_to_block(energy)


#####################################################################
# 1d. Agent with memory                                             #
# Default strategy: the reflex agent. The agent remembers the       #
# closest distance it has reached to the block and when. If it has  #
# not come closer for TIMEOUT ms it is probably stuck, so it        #
# switches strategy: back up and turn, then drive forward a while,  #
# then go back to the default strategy (see Figure 2 in the lab).   #
#####################################################################
TIMEOUT = 5000        # ms without getting closer -> stuck
TURN_TIME = 1500      # ms backing up and turning
WANDER_TIME = 2000    # ms driving forward after the turn

memory = dict(collected=0,              # blocks collected, last time we checked
              bestDistance=float('inf'),
              lastProgressTime=0,
              turnUntil=0,
              escapeUntil=0,
              turnDirection=1)          # 1 = right, -1 = left, changes every escape

def memory_agent(simulationTime, left, right, energy):
    # a block was collected -> new target, forget the old distance
    if blocksCollected > memory["collected"]:
        memory["collected"] = blocksCollected
        memory["bestDistance"] = float('inf')
        memory["lastProgressTime"] = simulationTime

    # remember when we last came closer to the block
    if energy.distance < memory["bestDistance"] - 0.05:
        memory["bestDistance"] = energy.distance
        memory["lastProgressTime"] = simulationTime

    # stuck for too long -> start the alternative strategy
    if simulationTime >= memory["escapeUntil"] and \
       simulationTime - memory["lastProgressTime"] > TIMEOUT:
        print("Stuck, trying something else...")
        memory["turnDirection"] *= -1
        memory["turnUntil"] = simulationTime + TURN_TIME
        memory["escapeUntil"] = simulationTime + TURN_TIME + WANDER_TIME
        # start measuring progress again after the escape
        memory["bestDistance"] = float('inf')
        memory["lastProgressTime"] = memory["escapeUntil"]

    # alternative strategy, part 1: back up while turning
    if simulationTime < memory["turnUntil"]:
        d = memory["turnDirection"]
        return dict(speedLeft=-SPEED * 0.5 + TURN_SPEED * d,
                    speedRight=-SPEED * 0.5 - TURN_SPEED * d)
    # alternative strategy, part 2: drive forward, but still avoid walls
    if simulationTime < memory["escapeUntil"]:
        wallAction = avoid_walls(left, right)
        if wallAction is not None:
            return wallAction
        return dict(speedLeft=SPEED, speedRight=SPEED)

    # default strategy
    return reflex_agent(simulationTime, left, right, energy)



#############################################################################
# MAIN
#############################################################################

agents = dict(random=random_agent, fixed=fixed_agent,
              reflex=reflex_agent, memory=memory_agent)
agent = agents[AGENT]
blocksCollected = 0

# connect to the server
robot = World.init()
# print important parts of the robot
print(sorted(robot.keys()))

while robot: # main Control loop
    #######################################################
    # Perception Phase: Get information about environment #
    #######################################################
    simulationTime = World.getSimulationTime()
    left = World.getSensorReading("ultraSonicSensorLeft")
    right = World.getSensorReading("ultraSonicSensorRight")
    energy = World.getSensorReading("energySensor")
    if simulationTime%1000==0:
        # print some useful info, but not too often
        print ('Time:',simulationTime,\
               'ultraSonicSensorLeft:',left,\
               "ultraSonicSensorRight:", right)

    # collected blocks are moved far away (1000, 1000), so if the nearest
    # block is that far away, all blocks have been collected
    if energy.distance > 100:
        print("All blocks collected!")
        World.STOP()
        break

    ##############################################
    # Reasoning: figure out which action to take #
    ##############################################
    motorSpeed = agent(simulationTime, left, right, energy)

    ########################################
    # Action Phase: Assign speed to wheels #
    ########################################
    # assign speed to the wheels
    World.setMotorSpeeds(motorSpeed)
    # try to collect energy block (will fail if not within range)
    if World.collectNearestBlock() == 'Energy collected :)':
        blocksCollected += 1
        print("Energy collected! Blocks collected:", blocksCollected)
