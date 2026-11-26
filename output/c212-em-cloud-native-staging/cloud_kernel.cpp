// SI prescribed fields and synchronized Boris. Caller-owned scratch buffers;
// fixed source order per particle, no reductions or persistent mutable state.
#include <algorithm>
#include <cmath>
#include <vector>
#include <immintrin.h>
#include <intrin.h>

#define C2API extern "C" __declspec(dllexport)
using V = double[3];
constexpr double PositionLimit = 1e17;

static double dot(const double* a, const double* b) noexcept {
    return (a[0]*b[0]+a[1]*b[1])+a[2]*b[2];
}
static double norm(const double* a) noexcept {
    const double scale = std::max({std::abs(a[0]), std::abs(a[1]), std::abs(a[2])});
    // Coordinates are bounded to1e17m. Preserve subnormal exclusions as well.
    if (scale < 1e-150 || scale > 1e150) return std::hypot(a[0], a[1], a[2]);
    return std::sqrt(dot(a,a));
}
static bool finite(const double* a) noexcept {
    return std::isfinite(a[0]) && std::isfinite(a[1]) && std::isfinite(a[2]);
}
static bool position(const double* a) noexcept {
    return finite(a) && std::abs(a[0])<=PositionLimit &&
        std::abs(a[1])<=PositionLimit && std::abs(a[2])<=PositionLimit;
}
static bool speed(const double* a, double limit) noexcept {
    if (!finite(a)) return false;
    const double r=norm(a);
    if (std::abs(r-limit)<=1e-12*limit) return std::hypot(a[0],a[1],a[2])<=limit;
    return r<=limit;
}
static void cross(const double* a, const double* b, double* out) noexcept {
    out[0]=a[1]*b[2]-a[2]*b[1];
    out[1]=a[2]*b[0]-a[0]*b[2];
    out[2]=a[0]*b[1]-a[1]*b[0];
}
static void add(double& sum, double& compensation, double term) noexcept {
    const double y=term-compensation;
    const double next=sum+y;
    compensation=(next-sum)-y;
    sum=next;
}

// Packed sources: xyz, exclusion radius, charge, magnetic moment xyz (8f64).
static int field(int ns, const double* sources, const double* e0, const double* b0,
    const double* x, double ke, double mu4pi, bool potential,
    double* e, double* b, double& phi) noexcept {
    if (!position(x)) return 4;
    V ec{},bc{};
    for (int k=0;k<3;++k) { e[k]=e0[k];b[k]=b0[k]; }
    phi=potential ? -dot(x,e0) : 0.;double pc=0.;
    for (int j=0;j<ns;++j) {
        const double* src=sources+j*8;
        V delta{x[0]-src[0],x[1]-src[1],x[2]-src[2]};
        const double radius=norm(delta);
        if (!std::isfinite(radius) || radius<=src[3]) return 2;
        V direction{delta[0]/radius,delta[1]/radius,delta[2]/radius};
        if (src[4]!=0.) {
            const double strength=(ke*src[4]/radius)/radius;
            for (int k=0;k<3;++k) add(e[k],ec[k],strength*direction[k]);
            if (potential) add(phi,pc,ke*src[4]/radius);
        }
        if (src[5]!=0. || src[6]!=0. || src[7]!=0.) {
            const double strength=((mu4pi/radius)/radius)/radius;
            const double along=dot(direction,src+5);
            for (int k=0;k<3;++k)
                add(b[k],bc[k],strength*(3*direction[k]*along-src[5+k]));
        }
    }
    return finite(e) && finite(b) && (!potential || std::isfinite(phi)) ? 0 : 3;
}

static int drift(int ns, const double* sources, const double* a, const double* b) noexcept {
    if (!position(a) || !position(b)) return 4;
    V delta{b[0]-a[0],b[1]-a[1],b[2]-a[2]};
    for (int j=0;j<ns;++j) {
        const double* src=sources+j*8;
        V nearest{},offset{};bool separate=false;
        for (int k=0;k<3;++k) {
            nearest[k]=src[k]-std::clamp(src[k],std::min(a[k],b[k]),std::max(a[k],b[k]));
            if (std::abs(nearest[k])>src[3]) { separate=true;break; }
        }
        if (separate) continue;
        if (norm(nearest)>src[3]) continue;
        for (int k=0;k<3;++k) offset[k]=src[k]-a[k];
        const double scale=std::max({std::abs(delta[0]),std::abs(delta[1]),std::abs(delta[2])});
        if (scale>0) {
            V unit{delta[0]/scale,delta[1]/scale,delta[2]/scale};
            V scaled{offset[0]/scale,offset[1]/scale,offset[2]/scale};
            double fraction=dot(scaled,unit)/dot(unit,unit);
            if (!std::isfinite(fraction)) return 3;
            fraction=std::clamp(fraction,0.,1.);
            for (int k=0;k<3;++k) offset[k]-=fraction*delta[k];
        }
        if (norm(offset)<=src[3]) return 2;
    }
    return 0;
}

// An outward-rounded box contains every drift of the batch. Discard only
// sources whose exclusion sphere is provably separated on at least one axis.
// This filters domain tests; every source still contributes to E and B.
static std::vector<double> drift_sources(int n,int ns,const double* sources,
    const double* a,const double* b) {
    V lo{a[0],a[1],a[2]},hi{a[0],a[1],a[2]};
    for (int i=0;i<n;++i) for (int k=0;k<3;++k) {
        lo[k]=std::min(lo[k],std::min(a[i*3+k],b[i*3+k]));
        hi[k]=std::max(hi[k],std::max(a[i*3+k],b[i*3+k]));
    }
    for (int k=0;k<3;++k) {
        lo[k]=std::nextafter(lo[k],-INFINITY);
        hi[k]=std::nextafter(hi[k],INFINITY);
    }
    std::vector<double> active;active.reserve(ns*8);
    for (int j=0;j<ns;++j) {
        const double* src=sources+j*8;bool separate=false;
        for (int k=0;k<3;++k) {
            const double distance=std::nextafter(std::abs(src[k]-std::clamp(src[k],lo[k],hi[k])),0.);
            if (distance>std::nextafter(src[3],INFINITY)) { separate=true;break; }
        }
        if (!separate) active.insert(active.end(),src,src+8);
    }
    return active;
}

// Four independent particles per register. Keep the original source order
// and Kahan sequence in every lane; no approximate reciprocal or fused FMA.
static bool field4(int ns, const double* sources, const double* e0, const double* b0,
    const double* x, double ke, double mu4pi, bool potential,
    double* e, double* b, double* phi) noexcept {
    for (int lane=0;lane<4;++lane) if (!position(x+lane*3)) return false;
    const __m256d zero=_mm256_setzero_pd();
    const __m256d three=_mm256_set1_pd(3.);
    __m256d xyz[3],ev[3],bv[3],ec[3],bc[3];
    for (int k=0;k<3;++k) {
        xyz[k]=_mm256_set_pd(x[9+k],x[6+k],x[3+k],x[k]);
        ev[k]=_mm256_set1_pd(e0[k]);bv[k]=_mm256_set1_pd(b0[k]);ec[k]=bc[k]=zero;
    }
    __m256d pv=zero,pc=zero;
    if (potential) {
        pv=_mm256_add_pd(_mm256_add_pd(_mm256_mul_pd(xyz[0],ev[0]),
             _mm256_mul_pd(xyz[1],ev[1])),_mm256_mul_pd(xyz[2],ev[2]));
        pv=_mm256_sub_pd(zero,pv);
    }
    const auto add4=[](__m256d& sum,__m256d& comp,__m256d term) {
        const __m256d y=_mm256_sub_pd(term,comp);
        const __m256d next=_mm256_add_pd(sum,y);
        comp=_mm256_sub_pd(_mm256_sub_pd(next,sum),y);sum=next;
    };
    for (int j=0;j<ns;++j) {
        const double* src=sources+j*8;__m256d d[3],direction[3];
        for (int k=0;k<3;++k) d[k]=_mm256_sub_pd(xyz[k],_mm256_set1_pd(src[k]));
        const __m256d radius=_mm256_sqrt_pd(_mm256_add_pd(
            _mm256_add_pd(_mm256_mul_pd(d[0],d[0]),_mm256_mul_pd(d[1],d[1])),_mm256_mul_pd(d[2],d[2])));
        if (_mm256_movemask_pd(_mm256_cmp_pd(radius,_mm256_set1_pd(1e-100),_CMP_LT_OQ)) ||
            _mm256_movemask_pd(_mm256_cmp_pd(radius,_mm256_set1_pd(src[3]),_CMP_LE_OQ))) return false;
        // One correctly rounded division; multiplication regrouping is tested
        // against the scalar reference. Tiny radii retain its original order.
        const __m256d inverse=_mm256_div_pd(_mm256_set1_pd(1.),radius);
        for (int k=0;k<3;++k) direction[k]=_mm256_mul_pd(d[k],inverse);
        if (src[4]!=0.) {
            const __m256d coulomb=_mm256_mul_pd(_mm256_set1_pd(ke*src[4]),inverse);
            const __m256d strength=_mm256_mul_pd(coulomb,inverse);
            for (int k=0;k<3;++k) add4(ev[k],ec[k],_mm256_mul_pd(strength,direction[k]));
            if (potential) add4(pv,pc,coulomb);
        }
        if (src[5]!=0. || src[6]!=0. || src[7]!=0.) {
            const __m256d strength=_mm256_mul_pd(_mm256_mul_pd(_mm256_mul_pd(
                _mm256_set1_pd(mu4pi),inverse),inverse),inverse);
            const __m256d along=_mm256_add_pd(_mm256_add_pd(
                _mm256_mul_pd(direction[0],_mm256_set1_pd(src[5])),
                _mm256_mul_pd(direction[1],_mm256_set1_pd(src[6]))),
                _mm256_mul_pd(direction[2],_mm256_set1_pd(src[7])));
            for (int k=0;k<3;++k)
                add4(bv[k],bc[k],_mm256_mul_pd(strength,_mm256_sub_pd(
                    _mm256_mul_pd(_mm256_mul_pd(three,direction[k]),along),_mm256_set1_pd(src[5+k]))));
        }
    }
    double lanes[4];
    for (int k=0;k<3;++k) {
        _mm256_storeu_pd(lanes,ev[k]);for (int i=0;i<4;++i) e[i*3+k]=lanes[i];
        _mm256_storeu_pd(lanes,bv[k]);for (int i=0;i<4;++i) b[i*3+k]=lanes[i];
    }
    _mm256_storeu_pd(phi,pv);
    for (int i=0;i<4;++i)
        if (!finite(e+i*3) || !finite(b+i*3) || (potential && !std::isfinite(phi[i]))) return false;
    return true;
}

C2API int c2em_cloud_abi() noexcept { return 1; }
C2API int c2em_cloud_avx2() noexcept {
    int bits[4];__cpuid(bits,0);if (bits[0]<7) return 0;
    __cpuidex(bits,1,0);
    if (!(bits[2]&(1<<27)) || !(bits[2]&(1<<28)) || (_xgetbv(0)&6)!=6) return 0;
    __cpuidex(bits,7,0);return (bits[1]&(1<<5))!=0;
}

C2API int c2em_cloud_fields(int n, int ns, const double* x, const double* sources,
    const double* e0, const double* b0, double ke, double mu4pi, int potential,
    int threads, double* e, double* b, double* phi, int* bad) noexcept {
    if (n<1 || n>10000 || ns<0 || ns>128 || threads<1 || threads>8 ||
        !x || !sources || !e0 || !b0 || !e || !b || !phi || !bad) return 1;
    try {
        std::vector<int> errors(n,0);
        const int groups=n/4;
        #pragma omp parallel for num_threads(threads) if(n>=512)
        for (int group=0;group<groups;++group) {
            const int base=group*4;
            if (ns>=4 && field4(ns,sources,e0,b0,x+base*3,ke,mu4pi,potential!=0,e+base*3,b+base*3,phi+base)) continue;
            for (int i=base;i<base+4;++i)
                errors[i]=field(ns,sources,e0,b0,x+i*3,ke,mu4pi,potential!=0,e+i*3,b+i*3,phi[i]);
        }
        for (int i=groups*4;i<n;++i)
            errors[i]=field(ns,sources,e0,b0,x+i*3,ke,mu4pi,potential!=0,e+i*3,b+i*3,phi[i]);
        for (int i=0;i<n;++i) if (errors[i]) { *bad=i;return errors[i]; }
        return 0;
    } catch (...) { return 7; }
}

C2API int c2em_cloud_step(int n, int ns, const double* x, const double* v,
    const double* q, const double* mass, const double* sources,
    const double* e0, const double* b0, double ke, double mu4pi,
    double dt, double speed_limit, int electric, int magnetic, int threads,
    double* outx, double* outv, double* work, double* kinetic, int* bad) noexcept {
    if (n<1 || n>10000 || ns<0 || ns>128 || threads<1 || threads>8 ||
        !x || !v || !q || !mass || !sources || !e0 || !b0 ||
        !outx || !outv || !work || !kinetic || !bad ||
        !std::isfinite(dt) || dt<=0 || !std::isfinite(speed_limit) || speed_limit<=0 ||
        (electric!=0 && electric!=1) || (magnetic!=0 && magnetic!=1)) return 1;
    try {
        std::vector<int> errors(n,0);
        std::vector<double> mids(n*3),es(n*3),bs(n*3),phis(n);
        #pragma omp parallel for num_threads(threads) if(n>=512)
        for (int i=0;i<n;++i) {
            const double* xi=x+i*3;const double* vi=v+i*3;
            if (!position(xi) || !speed(vi,speed_limit) || !std::isfinite(q[i]) ||
                !std::isfinite(mass[i]) || mass[i]<=0) { errors[i]=1;continue; }
            double* mid=mids.data()+i*3;
            for (int k=0;k<3;++k) mid[k]=xi[k]+.5*dt*vi[k];
            if (!position(mid)) errors[i]=4;
        }
        for (int i=0;i<n;++i) if (errors[i]) { *bad=i;return errors[i]; }
        const auto first_sources=drift_sources(n,ns,sources,x,mids.data());
        const int first_count=static_cast<int>(first_sources.size()/8);
        if (first_count) {
            #pragma omp parallel for num_threads(threads) if(n>=512)
            for (int i=0;i<n;++i) errors[i]=drift(first_count,first_sources.data(),x+i*3,mids.data()+i*3);
            for (int i=0;i<n;++i) if (errors[i]) { *bad=i;return errors[i]; }
        }
        const int field_error=c2em_cloud_fields(n,ns,mids.data(),sources,e0,b0,ke,mu4pi,0,threads,
            es.data(),bs.data(),phis.data(),bad);
        if (field_error) return field_error;
        #pragma omp parallel for num_threads(threads) if(n>=512)
        for (int i=0;i<n;++i) {
            const double* xi=x+i*3;const double* vi=v+i*3;const double* mid=mids.data()+i*3;
            double* xo=outx+i*3;double* vo=outv+i*3;
            double* e=es.data()+i*3;double* b=bs.data()+i*3;
            V t{},minus{},s{},inner{},outer{},temporary{},plus{};
            const double half=.5*dt*(q[i]/mass[i]);
            for (int k=0;k<3;++k) {
                if (!electric) e[k]=0.;
                if (!magnetic) b[k]=0.;
                t[k]=half*b[k];minus[k]=vi[k]+half*e[k];
            }
            if (!finite(t) || norm(t)>.05) { errors[i]=6;continue; }
            const double denominator=1+dot(t,t);
            for (int k=0;k<3;++k) s[k]=2*t[k]/denominator;
            cross(minus,t,inner);
            for (int k=0;k<3;++k) temporary[k]=minus[k]+inner[k];
            cross(temporary,s,outer);
            for (int k=0;k<3;++k) {
                plus[k]=minus[k]+outer[k];vo[k]=plus[k]+half*e[k];
                xo[k]=mid[k]+.5*dt*vo[k];
            }
            if (!finite(minus) || !finite(plus) || !finite(vo) || !finite(xo)) { errors[i]=3;continue; }
            if (!speed(minus,speed_limit) || !speed(plus,speed_limit) || !speed(vo,speed_limit)) { errors[i]=5;continue; }
            if (!position(xo)) { errors[i]=4;continue; }
            V moved{xo[0]-xi[0],xo[1]-xi[1],xo[2]-xi[2]};
            work[i]=q[i]*dot(e,moved);
            kinetic[i]=.5*mass[i]*(dot(vo,vo)-dot(vi,vi));
            if (!std::isfinite(work[i]) || !std::isfinite(kinetic[i])) errors[i]=3;
        }
        for (int i=0;i<n;++i) if (errors[i]) { *bad=i;return errors[i]; }
        const auto last_sources=drift_sources(n,ns,sources,mids.data(),outx);
        const int last_count=static_cast<int>(last_sources.size()/8);
        if (last_count) {
            #pragma omp parallel for num_threads(threads) if(n>=512)
            for (int i=0;i<n;++i) errors[i]=drift(last_count,last_sources.data(),mids.data()+i*3,outx+i*3);
            for (int i=0;i<n;++i) if (errors[i]) { *bad=i;return errors[i]; }
        }
        return 0;
    } catch (...) { return 7; }
}
