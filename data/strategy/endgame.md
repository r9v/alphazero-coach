# Endgame Theory

Connect 4 is a solved game. Understanding endgame principles helps explain why the AlphaZero engine makes the moves it does in late-game positions.

## The Solved Game

Connect 4 was independently solved by James Dow Allen (October 1, 1988) and Victor Allis (October 16, 1988). Player 1 wins with perfect play when starting in the center column. The first player can force a win on or before the 41st move out of 42 total moves. The total number of possible board positions is approximately 4.5 trillion.

## Endgame Zugzwang Control

In the endgame, the board is mostly filled and each move is critical. The player who controls zugzwang can force the opponent to make a losing move. This control comes from maintaining the correct threat parity throughout the game. The controlling player has engineered the position so that when the opponent is forced to fill remaining squares, they fill the square below the controller's winning threat.

## Counting Remaining Moves

As the board fills, remaining move count becomes concrete. If the number of remaining empty squares is odd, Player 1 makes the last move. If even, Player 2 makes the last move. A player with a threat that will be reached on their turn based on remaining square count has a winning endgame.

## Allis's Nine Strategic Rules

Victor Allis identified nine rules for endgame control, primarily describing how the player controlling zugzwang guarantees certain squares will be filled by the correct player:

1. **Claimeven**: The controller ensures they eventually play on even-row squares by waiting for the opponent to fill the odd square below first.
2. **Baseinverse**: If two adjacent bottom-row squares are both accessible, you can claim one when your opponent claims the other.
3. **Vertical**: You can always block a vertical four-in-a-row by playing one of the two critical squares in a column.
4. **Aftereven**: If a group can be completed using squares claimable via Claimeven, the controller will eventually complete it.
5. **Lowinverse**: A rule about controlling pairs of lower squares across columns.
6. **Highinverse**: Similar to Lowinverse but for higher board positions.
7. **Baseclaim**: A combination rule involving base row and claiming mechanics.
8. **Before**: A rule about ordering threats to ensure they resolve in the controller's favor.
9. **Specialbefore**: A refined version of the Before rule for specific configurations.

## Practical Endgame Guidelines

1. Count remaining moves to determine whose turn it will be when critical squares need to be filled.
2. Identify which threats are still alive and on which rows they sit.
3. Check whether your threats fall on rows that align with your parity advantage.
4. Try to control which columns fill first, as this affects when critical squares become playable.
5. Avoid filling below opponent's threats — every piece you place raises the playable height in a column.
6. Playing in a non-critical column can change the parity of remaining moves, which may be strategically decisive.
