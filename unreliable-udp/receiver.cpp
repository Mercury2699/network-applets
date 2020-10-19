#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <netdb.h>
#include <netinet/in.h>
#include <unistd.h>
#include <iostream>
#include <fstream>


// receiver <file name> <timeout>
int main(int argc, char *argv[]) {
    char filename[100];
    int timeout, sockretval;
    struct sockaddr_in senderaddr;
    unsigned char buf[2048];
    unsigned int recvlen, addrlen; 

    if (argc == 3){
        strcpy(filename, argv[1]);
        timeout = atoi(argv[2]);
    } else {
        printf("Usage: receiver <file name> <timeout> \n");
    }
    
    if ((sockretval = socket(AF_INET, SOCK_DGRAM, 0)) < 0){ 
        perror("socket creation failed"); 
        return 1; 
    }

    // memset((char *)&senderaddr, 0, sizeof(senderaddr));
    senderaddr.sin_family = AF_INET;
    senderaddr.sin_addr.s_addr = htonl(INADDR_ANY);
    senderaddr.sin_port = htons(0);

    if (bind(sockretval, (struct sockaddr *)&senderaddr, sizeof(senderaddr)) < 0) {
        perror("bind failed");
        return 1;
    }

    int portnum = senderaddr.sin_port;

    std::ofstream portfile("port");  
    portfile << portnum << std::endl;  
    portfile.close();


    std::ofstream recvdfile(filename);  
    for (;;) {
        printf("waiting on port %d\n", portnum);
        recvlen = recvfrom(sockretval, buf, 2048, 0, (struct sockaddr *)&senderaddr, &addrlen);
        printf("received %d bytes\n", recvlen);
        if (recvlen > 0){
            buf[recvlen] = 0;
            printf("received message: \"%s\"\n", buf);
        }
        recvdfile << buf;
    }
    recvdfile.close();

    close(sockretval);

    return 0;
}
