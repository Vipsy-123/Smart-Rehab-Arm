import numpy as np
import matplotlib.pyplot as plt
import skfuzzy as fuzz
import skfuzzy.control as ctrl

def plot_membership_functions():
    # Create figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Fuzzy Logic Membership Functions', fontsize=16)

    # Goal Difference Membership Functions
    goal_difference = ctrl.Antecedent(np.arange(-100, 101, 1), 'goal_difference')
    goal_difference['near'] = fuzz.trimf(goal_difference.universe, [-100, 0, 100])
    goal_difference['below_goal'] = fuzz.trimf(goal_difference.universe, [-100, -50, 0])
    goal_difference['above_goal'] = fuzz.trimf(goal_difference.universe, [0, 50, 100])

    goal_difference.view(ax=ax1)
    ax1.set_title('Goal Difference Membership Functions')

    # EMG Signal Membership Functions
    emg_signal = ctrl.Antecedent(np.arange(0, 101, 1), 'emg_signal')
    emg_signal['low'] = fuzz.trimf(emg_signal.universe, [0, 0, 50])
    emg_signal['moderate'] = fuzz.trimf(emg_signal.universe, [25, 50, 75])
    emg_signal['high'] = fuzz.trimf(emg_signal.universe, [50, 100, 100])

    emg_signal.view(ax=ax2)
    ax2.set_title('EMG Signal Membership Functions')

    # Assist Decision Membership Functions
    assist_decision = ctrl.Consequent(np.arange(0, 101, 1), 'assist_decision')
    assist_decision['no'] = fuzz.trimf(assist_decision.universe, [0, 0, 50])
    assist_decision['maybe'] = fuzz.trimf(assist_decision.universe, [25, 50, 75])
    assist_decision['yes'] = fuzz.trimf(assist_decision.universe, [50, 100, 100])

    assist_decision.view(ax=ax3)
    ax3.set_title('Assist Decision Membership Functions')

    # Timeout Duration Membership Functions
    timeout_duration = ctrl.Consequent(np.arange(0, 101, 1), 'timeout_duration')
    timeout_duration['short'] = fuzz.trimf(timeout_duration.universe, [0, 0, 30])
    timeout_duration['medium'] = fuzz.trimf(timeout_duration.universe, [15, 30, 45])
    timeout_duration['long'] = fuzz.trimf(timeout_duration.universe, [30, 60, 60])

    timeout_duration.view(ax=ax4)
    ax4.set_title('Timeout Duration Membership Functions')

    # Adjust layout and display
    plt.tight_layout()
    plt.show()

# Call the function to generate the plots
plot_membership_functions()