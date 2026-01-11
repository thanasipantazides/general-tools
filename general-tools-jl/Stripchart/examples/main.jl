using Stripchart
using Sockets

function main(ip::IPv4, port::Int; group::IPv4="")
    # udp_listen(ip, port; group)
    sock = udp_setup(ip, port; group)
    
    while true
        data = recv(sock)
        if length(data) == Stripchart.frame_size_rtd
            t,f,T = parse_rtd(data, timestyle=:remote)
            println(t, ", ", T)
        end
    end
end