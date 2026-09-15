# Quantum Reinforcement Profile

## Use

Use for policy-gradient, DQN, or actor-critic variants with a quantum policy or value model.

## Variant Scope

- `policy_gradient`: stochastic policy with an explicit log-probability gradient objective.
- `dqn`: action-value model with target-network and replay semantics.
- `actor_critic`: separate or shared policy and value contracts.

A fixed list of action values or an argmax smoke is not a trained reinforcement-learning
agent.

## Data and Encoding

Record environment and version, observation and action spaces, observation preprocessing,
episode horizon, termination versus truncation, reward scaling, action mapping, and seeds.
Preprocessing state must be frozen for evaluation.

## Model and Training

Define policy or value circuit, classical components, exploration, replay or rollout rules,
discounting, target updates where applicable, optimizer, gradient method, batch construction,
evaluation cadence, and checkpoint state. Keep training and evaluation environments separate.

## Measurement and Output

The operation is `act`. Define whether output is an action distribution, sampled action, or
action values, including legal-action masking and deterministic evaluation behavior. Persist
all normalization, policy/value, target-network, and action-mapping state.

## Diagnostics

Separate training and evaluation episodes. Report reward distribution, success rate, seed
variance, sample efficiency, environment parity, policy stability, and a matched classical
agent. Never infer an advantage from one successful episode.

## Failure Modes

- Training episodes reused as independent evaluation.
- Environment, reward, or action mapping differs between baselines.
- Missing replay, target network, critic, or log-probability semantics for the named variant.
- Policy collapses to a constant action or evaluation remains exploratory.
- Checkpoint omits normalization or target-network state.

## Acceptance

Require executable environment metadata, correct variant-specific update semantics, separated
evaluation episodes, reward and success distributions over declared seeds, matched classical
agent, complete checkpoint reload, and a deterministic known-observation `act` fixture.
