
module Stripchart

using Sockets

const frame_size_rtd = 42

include("listen.jl")

export udp_setup, parse_rtd

end # module Stripchart
