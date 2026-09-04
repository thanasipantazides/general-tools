# Live stripchart for Housekeeping data
This is a GSE software for plotting FOXSI housekeeping data—currents, voltages, and temperatures—as they arrive and are logged by the main GSE.

## Running
Run this in a Julia environment. To start the environment for this project, navigate into `general-tools/general-tools-jl/Stripchart` and do:
```bash
julia --project=.
```
This will launch the Julia REPL, and give you a command prompt that looks like `julia> `. Then compile the script using:
```
julia> include("examples/main.jl")
```
Now it will think for a little bit. When it's done, run like this (put in the path to your own log folder):
```
julia> run("absolute/path/to/latest/log/folder/17-4-2024_11-41-21/")
```
**You will need to run the main FOXSI GSE before this to start plotting.** Otherwise this GUI will not find any new data to display.

If you are running this on the main FOXSI GSE computer, you could also just run:
```
julia> run()
```
and it will automatically find the latest log folder.