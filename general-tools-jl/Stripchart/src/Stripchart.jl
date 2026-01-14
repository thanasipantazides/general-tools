
module Stripchart

using Sockets

const frame_size_rtd = 42
const frame_size_pow = 38

include("listen.jl")
include("plot.jl")

# export System
# export PacketType
export udp_setup, parse_rtd, parse_pow, parse_time, parse_tlm, sys_type
export stripchart, Printer, push!

end # module Stripchart
