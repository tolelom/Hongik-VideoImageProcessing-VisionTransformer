import math
import numpy as np
from torch import nn
import torch

class MultiheadAttention(nn.Module):
    def __init__(self, input_dim, embed_dim, num_head):
        super().__init__()

        self.embed_dim = embed_dim
        self.num_head = num_head
        self.head_dim = embed_dim // num_head

        # stack weight 
        self.qkv_proj = nn.Linear(input_dim, 3*embed_dim)
        self.o_proj = nn.Linear(embed_dim, embed_dim)

        self.reset_parameters()


    def reset_parameters(self):
        #xavier init
        nn.init.xavier_uniform_(self.qkv_proj.weight)
        self.qkv_proj.bias.data.fill_(0)

        nn.init.xavier_uniform_(self.o_proj.weight)
        self.o_proj.bias.data.fill_(0)

    def scaled_dot_product(self, q, k, v, mask=None):
        d_k = q.size()[-1]
        attn_logits = torch.matmul(q, k.transpose(-2, -1))
        attn_logits = attn_logits / math.sqrt(d_k)

        if mask is not None:
            attn_logits = attn_logits.masked_fill(mask == 0, -1e10)

        attention = torch.nn.functional.softmax(attn_logits, dim=-1)
        
        values = torch.matmul(attention, v)
        return values, attention


    def forward(self, x, mask=None, return_attention=False):
        batch_size, seq_length, _ = x.size()
        qkv = self.qkv_proj(x)

        # separate Q, K, V 
        qkv = qkv.reshape(batch_size, seq_length, self.num_heads, self.head_dim * 3)
        qkv = qkv.permute(0, 2, 1, 3) # (batch, head, seq_len, dim)
        q, k, v = qkv.chunk(3, dim=-1)

        # determine value output
        values, attention = self.scaled_dot_product(q, k, v, mask=mask)
        values = values.permute(0, 2, 1, 3) # [batch, seq_len, Head, dim]
        values = values.reshape(batch_size, seq_length, self.embed_dim)
        output = self.o_proj(values)

        if return_attention:
            return output, attention
        else:
            return output

class MLP(nn.Module):
    def __init__(self, emb_size: int, expansion: int = 4, drop_rate: float = 0.):
        super().__init__()

        self.feedforward = nn.Sequential(
            nn.Linear(emb_size, expansion * emb_size),
            nn.GELU(),
            nn.Dropout(drop_rate),
            nn.Linear(expansion * emb_size, emb_size),
            nn.Dropout(drop_rate)
         )
        
    def forword(self,x):
      return self.feedforward(x)



class ResidualAdd(nn.Module):
    def __init__(self, fn):
        super.__init__()
        self.fn = fn

    def forward(self, x):
        res = x
        x = self.fn(x)
        x += res
        return x


class EncoderBlock(nn.Sequential):
    def __init__(self, dim, num_heads, ff_dim, dropout, **kwargs):
        super.__init__(
            ResidualAdd(nn.Sequential(
                nn.LayerNorm(dim),
                MultiheadAttention(dim, dim, num_heads),
                nn.Dropout(dropout)
            )),
            ResidualAdd((
                nn.LayerNorm(dim),
                MLP(dim),
                nn.Dropout(dropout)
            ))
        )

class Transformer(nn.Sequential):
    def __init__(self, depth : int = 12):
        super.__init__(*[EncoderBlock for _ in range(depth)])
        
