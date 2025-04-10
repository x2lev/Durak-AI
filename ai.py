class DurakEnv:
    def __init__(self, game_state):
        self.game_state = None
        self.done = False

    def reset(self):
        self.game_state = create_new_game()
        self.done = False
        return self.game_state

    def step(self, action):
        if self.done:
            raise Exception("Game is over. Call reset().")

        if action[0] == 'attack':
            self.game_state = apply_attack(self.game_state, action[1])
        elif action[0] == 'defend':
            self.game_state = apply_defend(self.game_state, action[1])

        reward = compute_reward(self.game_state)  # design this carefully
        self.done = check_game_over(self.game_state)
        return self.game_state, reward, self.done, {}
