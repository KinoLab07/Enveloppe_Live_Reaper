// usage: runfx fx.jsfx datadir srate nframes in.raw(nch interleaved f32 or "-") nin out.raw [slider=value ...] [tempo=120] [play=1]
// events during processing: name@sample=value (a slider), ps@sample=state (play_state: 0 stopped,
// 1 playing, 2 paused), beat@sample=qn (move the transport to that position)
// fx2=other.jsfx out2=out2.raw: a second plug-in run in the same process after the first one,
// with the same transport and silent input (like another track; gmem is shared). Its sliders
// and slider events are written with the prefix "B." (B.s3=1, B.s10@48000=1).
#include "ysfx.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <algorithm>
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
  struct Ev { long at; std::string k; double v; };
  std::vector<Ev> evs;   // "name@sample=value": set a slider during processing
  std::string fx2path, out2path;
  for(int i=8;i<argc;i++){ std::string a=argv[i]; auto e=a.find('='); std::string k=a.substr(0,e); double v=atof(a.c_str()+e+1);
    auto at=k.find('@');
    if(at!=std::string::npos){ evs.push_back({atol(k.c_str()+at+1),k.substr(0,at),v}); continue; }
    if(k=="fx2"){ fx2path=a.substr(e+1); continue; }
    if(k=="out2"){ out2path=a.substr(e+1); continue; }
    if(k=="tempo")tempo=v; else if(k=="play")play=(int)v; else sl.push_back({k,v}); }
  ysfx_t *fx2=nullptr;
  if(!fx2path.empty()){ fx2=ysfx_new(c); if(!ysfx_load_file(fx2,fx2path.c_str(),0)||!ysfx_compile(fx2,0)){fprintf(stderr,"fx2 fail\n");return 1;} ysfx_set_sample_rate(fx2,sr); ysfx_set_block_size(fx2,256); ysfx_init(fx2); }
  ysfx_init(fx);
  auto setsl2=[&](ysfx_t*x,const std::string&k,double v){ bool f=false; for(int i=0;i<256;i++) if(ysfx_slider_exists(x,i)){ const char*nm=ysfx_slider_get_name(x,i); if(k==nm||k==("s"+std::to_string(i+1))){ysfx_slider_set_value(x,i,v);f=true;} } return f; };
  for(auto&p:sl) if(p.first.rfind("B.",0)==0){ if(!fx2||!setsl2(fx2,p.first.substr(2),p.second)){fprintf(stderr,"no slider %s\n",p.first.c_str());return 1;} }
  sl.erase(std::remove_if(sl.begin(),sl.end(),[](auto&p){return p.first.rfind("B.",0)==0;}),sl.end());
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
  std::vector<float> outbuf, out2buf; double beat=0; int ps=play?1:2;
  auto setsl=[&](const std::string&k,double v){ for(int i=0;i<256;i++) if(ysfx_slider_exists(fx,i)){ const char*nm=ysfx_slider_get_name(fx,i); if(k==nm||k==("s"+std::to_string(i+1))) ysfx_slider_set_value(fx,i,v);} };
  for(long s=0;s<N;s+=B){ int n=(int)std::min<long>(B,N-s);
    for(auto&e:evs) if(e.at>=s && e.at<s+B){ if(e.k=="ps") ps=(int)e.v; else if(e.k=="beat") beat=e.v; else if(e.k.rfind("B.",0)==0){ if(fx2) setsl2(fx2,e.k.substr(2),e.v); } else setsl(e.k,e.v); }
    ysfx_time_info_t ti{}; ti.tempo=tempo; ti.playback_state=(ysfx_playback_state_t)ps; ti.time_position=beat*60./tempo; ti.beat_position=beat; ti.time_signature[0]=4; ti.time_signature[1]=4; ysfx_set_time_info(fx,&ti);
    for(int ch=0;ch<nch;ch++) for(int i=0;i<n;i++) ib[ch][i]= ch<nin? in[(size_t)(s+i)*nin+ch]:0.f;
    ysfx_process_float(fx,ip.data(),op.data(),nfin,nout,n);
    for(int i=0;i<n;i++) for(int ch=0;ch<nout;ch++) outbuf.push_back(ob[ch][i]);
    if(fx2){ ysfx_set_time_info(fx2,&ti); int o2=ysfx_get_num_outputs(fx2), i2=ysfx_get_num_inputs(fx2);
      std::vector<std::vector<float>> zb(std::max(i2,1),std::vector<float>(B,0.f)), ob2(std::max(o2,1),std::vector<float>(B));
      std::vector<const float*> zp; std::vector<float*> op2; for(auto&z:zb) zp.push_back(z.data()); for(auto&o:ob2) op2.push_back(o.data());
      ysfx_process_float(fx2,zp.data(),op2.data(),i2,o2,n);
      for(int i=0;i<n;i++) for(int ch=0;ch<o2;ch++) out2buf.push_back(ob2[ch][i]); }
    if(ps&1) beat+=n/sr*tempo/60.;
  }
  fwrite(outbuf.data(),4,outbuf.size(),fo); fclose(fo);
  if(fx2){ FILE*f2=fopen(out2path.c_str(),"wb"); fwrite(out2buf.data(),4,out2buf.size(),f2); fclose(f2);
    for(int i=0;i<256;i++) if(ysfx_slider_exists(fx2,i)) fprintf(stderr,"B.slider%d=%g\n",i+1,ysfx_slider_get_value(fx2,i)); }
  // SLIDERS_AT_END: final slider values, for tests of published status
  for(int i=0;i<256;i++) if(ysfx_slider_exists(fx,i)) fprintf(stderr,"slider%d=%g\n",i+1,ysfx_slider_get_value(fx,i));
  printf("%d\n",nout);
  return 0;
}
