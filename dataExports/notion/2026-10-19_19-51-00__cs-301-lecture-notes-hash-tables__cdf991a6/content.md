# CS 301 Lecture Notes: Hash Tables

## Key ideas
- A hash function maps keys to bucket indexes
- Collisions: chaining vs. open addressing
- Load factor α = n / m; resize when α \> 0.75
## Big-O
<table header-row="true">
<tr>
<td>Operation</td>
<td>Average</td>
<td>Worst</td>
</tr>
<tr>
<td>Insert</td>
<td>O(1)</td>
<td>O(n)</td>
</tr>
<tr>
<td>Lookup</td>
<td>O(1)</td>
<td>O(n)</td>
</tr>
</table>
## To do
- [ ] Finish lab 4 (hash map) before Friday
- [ ] Ask Prof. Nguyen about the amortized analysis proof
