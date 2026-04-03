# Odd/Even Threat Theory

Row parity is one of the most important strategic concepts in Connect 4. The row where a threat's completing square sits determines which player benefits from it.

## Core Definitions

- An **odd threat** is a three-in-a-row where the empty completing space sits on an odd-numbered row (rows 1, 3, 5 counting from bottom as row 1).
- An **even threat** is a three-in-a-row where the empty completing space sits on an even-numbered row (rows 2, 4, 6).

## The Parity Asymmetry

Player 1 (Red, moves first) benefits from odd threats. Player 2 (Yellow, moves second) benefits from even threats. This asymmetry arises from the alternating turn structure combined with gravity.

When a column fills from the bottom with alternating plays, Player 1 controls the odd rows (1, 3, 5) and Player 2 controls the even rows (2, 4, 6). An odd threat on row 3 or row 5 means that as pieces accumulate below, it will be Player 1's turn to fill that critical space.

## The Critical Rule

If Player 1 has an odd threat in one column and Player 2 has an even threat in a different column, Player 1's odd threat is stronger — Player 1 will win. For Player 2 to win through parity, they generally need at least two more odd-row advantages than Player 1, or the same number of odd threats plus at least one even threat.

## Shared vs Unshared Threats

An unshared odd-row threat belongs to only one player. A shared odd-row threat is a position where both players could potentially complete a line through the same row. Player 1 wins if they have one more unshared odd-row attack than Player 2, or the same number of unshared odd-row attacks plus an odd number of shared ones.

## Zugzwang and Parity

Zugzwang (German for "compulsion to move") is central to parity theory. When the board is nearly full, one player may be forced to place a piece beneath their opponent's threat, completing it for the opponent. Controlling zugzwang means controlling which player is forced to fill the critical squares. The number of remaining empty spaces determines whose turn occurs during endgame zugzwang sequences.

## Practical Application

- Player 1 should aim to create threats on odd rows (1, 3, 5).
- Player 2 should aim to create threats on even rows (2, 4, 6).
- When building threats, the ROW of the completing square is more important than the direction of the threat (horizontal, diagonal, etc.).
- Count remaining empty squares: if odd, Player 1 makes the last move; if even, Player 2 makes the last move.
