
---
title: "Advanced layer types: Sequences and Attention"
teaching: 50
exercises: 30
---

::: questions
- Why do we need layers specifically designed for sequential data?
- What are Recurrent Neural Networks (RNNs) and LSTMs?
- How does an LSTM "remember” important information over time?
- What are alternatives like attention?
:::

::: objectives
- Understand the structure and motivation behind RNN and LSTM layers
- Relate LSTM concepts to earlier architectures (dense, CNN)
- Explore a simple forecasting example using LSTM
:::

## Sequences are not just lists

In the previous episodes, we dealt with **tabular data** (e.g. penguins), and **image data** (e.g. Dollar Street), where the model processed inputs as independent examples.

But what happens when the **order of the data matters**?

- In **weather forecasting**, yesterday's temperature helps predict today's.
- In **text**, the word before "bank" helps us decide whether it's about money or rivers.
- In **biology**, DNA and protein sequences have important patterns based on order.

We need a model that can **use previous inputs to inform current predictions**. That's where **Recurrent Neural Networks (RNNs)** and **Long Short-Term Memory (LSTM)** layers come in.





## From Dense to Recurrent

In a dense layer, the network sees all the input at once. Each neuron connects to every input value.

In a CNN, filters move across the input (image or sequence), learning local patterns and reducing connections.

In a vanilla RNN, the network processes one input step at a time and reuses the same layer at each time step. What makes it "recurrent" is that it passes a hidden state between steps.



### Recurrent loop: how a vanilla RNN works

```
          ┌────────────┐
x_t ───►  │  RNN cell  │ ───► h_t
          └────────────┘
            ▲
         h_{t-1}
```

At each time step t, the RNN takes:
- the input at this step x_t
- the hidden state from the previous step h_{t-1}

It produces a new hidden state h_t, which is used for the next time step and sometimes for prediction.

This creates a short-term memory loop across the sequence.


## The problem with vanilla RNNs

Basic RNNs can capture short-term dependencies, but they struggle to retain information across long sequences — a limitation known as the vanishing gradient problem.

Imagine trying to predict the next word in a sentence:

> I grew up in France… I speak fluent ___.

You want the model to remember "France" — even if it happened many steps earlier. Vanilla RNNs often forget these long-range dependencies.



## LSTM to the rescue

LSTM (Long Short-Term Memory) layers address this by adding a memory component: the cell state.

```
          ┌────────────┐
x_t ───►  │  LSTM cell │ ───►   h_t
          └────────────┘
            ▲       ▲
        h_{t-1}   c_{t-1} (memory)
```

At each time step t, the LSTM takes:
- the input x_t
- the previous hidden state h_{t-1}
- the previous cell state c_{t-1}

The cell state acts as long-term memory, while the hidden state provides a short-term summary. Gates inside the LSTM control how much information to forget, store, or expose.

- **Forget gate**: What information should be erased from memory?
- **Input gate**: What new information should be stored?
- **Output gate**: What part of the memory should be passed forward?

This lets the model maintain a persistent internal state across many steps.

Unlike CNNs, LSTMs are not spatially structured, but **temporally structured**: they are great for time, text, or biological sequences.


## LSTM example: Forecasting temperature

Let's use the daily minimum temperature dataset from Melbourne (1981–1990).

```python
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

# Load data
url = "https://raw.githubusercontent.com/jbrownlee/Datasets/master/daily-min-temperatures.csv"
df = pd.read_csv(url, parse_dates=["Date"])

# Normalize and prepare sequences
scaler = MinMaxScaler()
data = scaler.fit_transform(df["Temp"].values.reshape(-1, 1))

def make_sequences(data, window=7):
    X, y = [], []
    for i in range(len(data) - window):
        X.append(data[i:i+window])
        y.append(data[i+window])
    return np.array(X), np.array(y)

X, y = make_sequences(data)
```

Train a basic LSTM model:

```python
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

model = Sequential([
    LSTM(32, input_shape=(X.shape[1], X.shape[2])),
    Dense(1)
])
model.compile(optimizer='adam', loss='mse')
model.fit(X, y, epochs=10, batch_size=16)
```

## Tying it back to earlier episodes

| Episode | What we did              | How LSTM builds on it                     |
|--------|--------------------------|-------------------------------------------|
| Dense  | Connected all inputs     | Still used inside LSTM layers             |
| CNN    | Shared filters for space | LSTM shares memory over time              |
| Dropout| Prevent overfitting      | Also used inside LSTM to regularize       |
| Optimizer | Used Adam              | Same optimizer, but gradients are harder  |


## Attention: A preview

LSTMs read inputs in order. But **attention** allows the model to "look around” the input and learn which parts are important — like reading with a highlighter.

In Keras:

```python
from tensorflow.keras.layers import Input, MultiHeadAttention, LayerNormalization

inputs = Input(shape=(100, 64))
attn_output = MultiHeadAttention(num_heads=2, key_dim=32)(inputs, inputs)
attn_output = LayerNormalization()(inputs + attn_output)
```

You don't have to understand this fully yet — just know that **attention** is a different strategy for processing sequences, used in Transformers and large language models (LLMs).



::: challenge
What are examples of sequence data in your domain?
- What would be a reasonable input representation?
- Would the order matter?
- Would a CNN, dense model, or LSTM make the most sense?
:::

::: keypoints
- RNNs and LSTMs allow neural networks to process data step-by-step
- LSTMs retain long-term context using gated memory
- Sequence models are widely used in time series, language, and biology
:::
