// usage: runfx fx.jsfx datadir srate nframes in.raw(nch interleaved f32 or "-") nin out.raw [slider=value ...] [tempo=120] [play=1]
#include "ysfx.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <string>
static void logr(intptr_t, ysfx_log_level l, const char *m){ fprintf(stderr,"[%s] %s\n",ysfx_log_level_string(l),m); }
int main(int argc,char**argv){
  ysfx_config_t *c=ysfx_config_new(); ysfx_register_builtin_audio_formats(c);
  ysfx_set_data_root(c,argv[2]); ysfx_set_log_reporter(c,logr);
  ysfx_set_import_root(c,argv[2]);
  ysfx_t *fx=ysfx_new(c);
  if(!ysfx_load_file(fx,argv[1],0)){fprintf(stderr,"load fail\n");return 1;}
  if(!ysfx_compile(fx,0)){fprintf(stderr,"compile fail\n");return 1;}
  double sr=atof(argv[3]); long N=atol(argv[4]); int nin=atoi(argv[6]);
  int nout=ysfx_get_num_outputs(fx); int nfin=ysfx_get_num_inputs(fx);
  ysfx_set_sample_rate(fx,sr); ysfx_set_block_size(fx,256);
  double tempo=120; int play=1;
  std::vector<std::pair<std::string,double>> sl;
  for(int i=8;i<argc;i++){ std::string a=argv[i]; auto e=a.find('='); std::string k=a.substr(0,e); double v=atof(a.c_str()+e+1);
    if(k=="tempo")tempo=v; else if(k=="play")play=(int)v; else sl.push_back({k,v}); }
  ysfx_init(fx);
  for(auto&p:sl){ bool f=false; for(int i=0;i<256;i++) if(ysfx_slider_exists(fx,i)){ const char*n=ysfx_slider_get_name(fx,i); if(p.first==n||p.first==("s"+std::to_string(i+1))){ysfx_slider_set_value(fx,i,p.second);f=true;} }
    if(!f){fprintf(stderr,"no slider %s\n",p.first.c_str());return 1;} }
  fprintf(stderr,"ins %d outs %d pdc %g\n",nfin,nout,ysfx_get_pdc_delay(fx));
  std::vector<float> in((size_t)N*nin,0.f);
  if(strcmp(argv[5],"-")){ FILE*f=fopen(argv[5],"rb"); fread(in.data(),4,in.size(),f); fclose(f);} 
  FILE*fo=fopen(argv[7],"wb");
  int B=256; int nch= nout>nin?nout:nin; if(nch<nfin)nch=nfin;
  std::vector<std::vector<float>> ib(nch,std::vector<float>(B)),ob(nch,std::vector<float>(B));
  std::vector<const float*> ip(nch); std::vector<float*> op(nch);
  for(int i=0;i<nch;i++){ip[i]=ib[i].data();op[i]=ob[i].data();}
  std::vector<float> outbuf; double beat=0;
  for(long s=0;s<N;s+=B){ int n=(int)std::min<long>(B,N-s);
    ysfx_time_info_t ti{}; ti.tempo=tempo; ti.playback_state=play?1:2; ti.time_position=s/sr; ti.beat_position=play? s/sr*tempo/60.:0; ti.time_signature[0]=4; ti.time_signature[1]=4; ysfx_set_time_info(fx,&ti);
    for(int ch=0;ch<nch;ch++) for(int i=0;i<n;i++) ib[ch][i]= ch<nin? in[(size_t)(s+i)*nin+ch]:0.f;
    ysfx_process_float(fx,ip.data(),op.data(),nfin,nout,n);
    for(int i=0;i<n;i++) for(int ch=0;ch<nout;ch++) outbuf.push_back(ob[ch][i]);
  }
  fwrite(outbuf.data(),4,outbuf.size(),fo); fclose(fo);
  printf("%d\n",nout);
  return 0;
}
