import random
import numpy as np
# Please feel free to work with your own code structure

# Rank: {2, 3, 4, 5, 6, 7, 8, 9, T, J, Q, K, A}
# Suit: {s, h, d, c}

# 2 example poker hands
example_hand1 = ['Ad', '2s', '2c']
example_hand2 = ['5s', '5c', '5d']

# Randomly generate two hands of n cards
def generate_2hands(nn_card=3):
    """
    Return two hands of cards, each hand consists of nn_card number of cards.
    Note that there shall be no duplicates.
    
    Parameters
    ----------
    nn_card : int
            Number of cards in each hand

    Returns
    -------
    out : lists of strings
        Two lists, each corresponding to one hand
    """
    card_ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    card_suits = ['s', 'h', 'd', 'c']
    
    my_deck = []
    for r in card_ranks:
        for s in card_suits:
            my_deck.append(r + s)
            
    random.shuffle(my_deck)
    
    p1_cards = my_deck[0 : nn_card]
    p2_cards = my_deck[nn_card : nn_card * 2]
    
    return p1_cards, p2_cards

# identify hand category using IF-THEN rule
def get_single_rank_value(rank_char):
    all_ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    return all_ranks.index(rank_char) + 1

def identify_hand(hand_):
    extracted_ranks = [item[0] for item in hand_]
    
    if extracted_ranks[0] == extracted_ranks[1] and extracted_ranks[1] == extracted_ranks[2]:
        return 'three_of_a_kind', get_single_rank_value(extracted_ranks[0])
    
    for r_val in set(extracted_ranks):
        if extracted_ranks.count(r_val) == 2:
            return 'pair', get_single_rank_value(r_val)
            
    top_val = 0
    for r_val in extracted_ranks:
        v = get_single_rank_value(r_val)
        if v > top_val:
            top_val = v
            
    high_card_tuple = ('high_card', top_val)
    return high_card_tuple

def analyse_hand(hand_):
    h_cat, h_str = identify_hand(hand_)
    final_score = 0
    
    if h_cat == 'high_card':
        final_score = h_str
    elif h_cat == 'pair':
        final_score = 13 + h_str
    elif h_cat == 'three_of_a_kind':
        final_score = 26 + h_str
        
    return final_score

#########################
#      Game flow        #
#########################


#########################
# phase 1: Card Dealing #
#########################


#########################
# phase 2:   Bidding    #
#########################

# Sensing, resoning & decision making, and acting


#########################
# phase 2:   Showdown   #
#########################
# --- Different Player Agent Behaviors ---

def strategy_random_agent():
    return random.randint(0, 50)

def strategy_fixed_agent():
    return 20

def strategy_reflex_agent(player_cards):
    cat, _ = identify_hand(player_cards)
    if cat == 'three_of_a_kind':
        return 45
    elif cat == 'pair':
        return 30
    else:
        return 5

def get_bid_amount(agent_type, cards):
    if agent_type == 'random':
        return strategy_random_agent()
    elif agent_type == 'fixed':
        return strategy_fixed_agent()
    elif agent_type == 'reflex':
        return strategy_reflex_agent(cards)
    return 0


# --- Main Experiment Runner ---

def run_experiment_trials(agent_a, agent_b, total_games=100, total_hands=50):
    difference_list = []
    
    for game_idx in range(total_games):
        score_a = 0
        score_b = 0
        
        for hand_idx in range(total_hands):
            c1, c2 = generate_2hands(3)
            pot_money = 0
            
            for turn in range(3):
                bid1 = get_bid_amount(agent_a, c1)
                bid2 = get_bid_amount(agent_b, c2)
                pot_money += (bid1 + bid2)
            
            val_a = analyse_hand(c1)
            val_b = analyse_hand(c2)
            
            if val_a > val_b:
                score_a += pot_money
            elif val_b > val_a:
                score_b += pot_money
                
        difference_list.append(score_a - score_b)
        
    mean_result = np.mean(difference_list)
    std_result = np.std(difference_list)
    return mean_result, std_result


# --- Execution and Printing Results ---

# Task 2d: Random vs Fixed
mean_2d, std_2d = run_experiment_trials('random', 'fixed')
print("Task 2d (Random vs Fixed):")
print("Mean Difference =", mean_2d, "| Std Dev =", std_2d)

print("\nTask 2e (Reflex evaluations):")
# Task 2e: Reflex vs Random
mean_2e1, std_2e1 = run_experiment_trials('reflex', 'random')
print("Reflex vs Random -> Mean =", mean_2e1, "| Std Dev =", std_2e1)

# Task 2e: Reflex vs Fixed
mean_2e2, std_2e2 = run_experiment_trials('reflex', 'fixed')
print("Reflex vs Fixed  -> Mean =", mean_2e2, "| Std Dev =", std_2e2)


