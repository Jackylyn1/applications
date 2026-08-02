the [ask for commmand, offer the existing commands and one free typing field to the user] path takes a very long time. Explain:
  - what takes so long (in detail e.g. output-generator uses 534 grep commands and 200 tail commands)
  - how we could solve this (e.g. batch, optimize context, ...)
  - if we can reduce this without breaking functionality
  - how much impact you expect by implementing this optimization
  If more than one commponent (e.g. command, agent, file, ...) is involved in this flow make sure that every coponent is analyzed
  Sort the output by highest impact on the complete flow in speed and token usage. List starts with the highest impact.