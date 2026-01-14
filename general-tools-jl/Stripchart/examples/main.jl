using Stripchart
using Sockets



function run(ip::IPv4, port::Int; group::String="")
    # udp_listen(ip, port; group)
    sock = udp_setup(ip, port; group=group)
    stripchart(sock)
    # while true
    #     data = recv(sock)
    #     ret = parse_tlm(data; verbose=false, timestyle=:local)
    #     if !isnothing(ret)
    #         println(ret[1], ": ", ret[3])
    #     end 
    #     # if length(data) == Stripchart.frame_size_rtd
    #     #     t,f,T = parse_rtd(data, timestyle=:remote)
    #     #     println(t, ", ", T)
    #     # end
    # end
end