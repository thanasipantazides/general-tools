#include <stdlib.h>
#include <stdio.h>
#include <dirent.h>
#include <string.h>

#define PSEP "/"
#ifdef _WIN32
    #define PSEP "\\"
#endif

// pixels in each direction
#define PX 2048UL
#define PY 1920UL
// bit depth of a pixel
#define TU unsigned short

int isfile(const char* fname_candidate) {
    const char* dot = strchr(fname_candidate, '.');
    if (dot != NULL && dot != fname_candidate && *(dot + 1) != '\0') {
        return 1;
    }
    return 0;
}

int isql(const char* fname_candidate) {
    if (isfile(fname_candidate)) {
        if (strstr(fname_candidate, "QL") != NULL) {
            return 1;
        }
    }
    return 0;
}

int write_ql(const char* fname, unsigned short img[]) {
    FILE *fh = fopen(fname, "wb");
    if (fh == NULL) {
        return -1;
    }
    fwrite(img, sizeof(unsigned short), PX*PY, fh);
    fclose(fh);
    return 0;
}

int write_pgm(const char* fname, unsigned short img[]) {
    FILE *fh = fopen(fname, "w");
    if (fh == NULL) {
        return -1;
    }
    
    unsigned long current_length = 0;
    const char header[53] = "P2\n# CMOS PGM writer for quicklook\n2048 1920\n65535";
    
    fputs(header, fh);
    // for (unsigned short i = 0; i < PX; ++i) {
    //     for (unsigned short j = 0; j < PY; ++j) {
    //         // printf("i=%6u, j=%6u, u=%u\n", i, j, i*PY + j);
    //         char thisbuf[7];
    //         fprintf(fh, "%6u", img[i*PY+j]);
    //         // fputs(thisbuf, fh);
    //     }
    //     fputs("\n", fh);
    // }
    for (unsigned short i = 0; i < PY; ++i) {
        for (unsigned short j = 0; j < PX; ++j) {
            // printf("i=%6u, j=%6u, u=%u\n", i, j, i*PY + j);
            char thisbuf[7];
            fprintf(fh, "%6u", img[i+j*PY]);
            // fputs(thisbuf, fh);
        }
        fputs("\n", fh);
    }
    fclose(fh);
    // current_length += snprintf(outbuff + current_length, BUFFER_SIZE - current_length, "%6u", this);
}

unsigned short read_buf[PX*PY];
unsigned short img_out[PX*PY] = {0};
unsigned long img_count = 0;
unsigned long wrong_size_count = 0;
unsigned long total_files = 0;

void move_average(unsigned short* img_old, unsigned short* img_new, unsigned long count) {    
    for (unsigned long ind = 0; ind < PX*PY; ++ind) {
        img_old[ind] = (img_new[ind] + count*img_old[ind]) / (count + 1);
    }
}

int main (int argc, char** argv) {
    if (argc < 4) {
        printf("run like this:\n\t>./mkpgm folder/of/input/files path/to/darkframe.dat path/to/output\n");
        return -1;
    }
    
    const char* search_dir = argv[1];
    const char* save_path = argv[3];
    printf("searching under %s\n", search_dir);
    printf("saving to %s\n", save_path);

    DIR *dir;
    struct dirent *entry;
    if ((dir=opendir(search_dir)) != NULL) {
        while ((entry=readdir(dir)) != NULL) {
            const char* fname = entry->d_name;
            if (isql(fname)) {
                char fullpath[PATH_MAX + 1];
                strcpy(fullpath, search_dir);
                strcat(fullpath, PSEP);
                strcat(fullpath, fname);
                // all files under dir...
                // printf("> %s\n", fname);
                FILE *fh = fopen(fullpath, "rb");
                if (fh == NULL) {
                    perror("Error opening file");
                    return -1;
                } else {
                    printf("> reading %s\n", fullpath);
                    unsigned long read_size = fread(read_buf, sizeof(unsigned short), PX*PY, fh);
                    if (read_size != PX*PY) {
                        printf("\twrong size, continuing.\n");
                        wrong_size_count++;
                        continue;
                    }
                    // printf("    got %i bytes\n", read_size);
                    // do the moving average....
                    move_average(img_out, read_buf, img_count);
                    img_count++;
                    fclose(fh);
                }
            }
        }
        closedir(dir);
        
        // write_ql(save_path, img_out);
        write_pgm(save_path, img_out);
        printf("> saved average output to %s\n", save_path);
        printf("> found %u files with wrong length out of %u\n", wrong_size_count, img_count);
        
    } else {
        // return -1;
        printf("> found nothing under %s.\n", search_dir);
    }
    return 0;
}