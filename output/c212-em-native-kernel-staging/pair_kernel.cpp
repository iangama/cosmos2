// Cosmos2 EM pair helper ABI1. Scalar IEEE operations, ordered pair reactions.
// No fast math/FMA, no model time or persistent mutable state in this DLL.
#include <algorithm>
#include <cmath>
#include <vector>

#define C2API extern "C" __declspec(dllexport)
C2API int c2em_pair_abi() noexcept { return 1; }

// Buffers: x/force[n*3], coupling/exclusion/radius/energy[np], delta[np*3].
// np=n*(n-1)/2. Caller owns independent contiguous float64 outputs.
C2API int c2em_pair_geometry(int n, const double* x, const double* coupling,
    const double* exclusion, double* force, double* delta, double* radius,
    double* energy) noexcept {
    if (n<1 || n>128 || !x || !coupling || !exclusion || !force || !delta || !radius || !energy) return 1;
    try {
        const int pairs=n*(n-1)/2;
        std::vector<double> contribution(pairs*3);
        std::fill(force,force+n*3,0.);
        int p=0;
        for(int i=0;i<n;++i) for(int j=i+1;j<n;++j,++p) {
            double* d=delta+p*3;
            for(int k=0;k<3;++k) d[k]=x[i*3+k]-x[j*3+k];
            const double r=std::sqrt((d[0]*d[0]+d[1]*d[1])+d[2]*d[2]);
            if(!std::isfinite(r) || r<=exclusion[p]) return 2;
            radius[p]=r;
            const double term=coupling[p]/r;
            energy[p]=term;
            const double magnitude=term/r;
            for(int k=0;k<3;++k) contribution[p*3+k]=magnitude*(d[k]/r);
        }
        // Preserve the former np.add.at/bincount accumulation order:
        // every i contribution, followed by every j reaction.
        p=0;
        for(int i=0;i<n;++i) for(int j=i+1;j<n;++j,++p)
            for(int k=0;k<3;++k) force[i*3+k]+=contribution[p*3+k];
        p=0;
        for(int i=0;i<n;++i) for(int j=i+1;j<n;++j,++p)
            for(int k=0;k<3;++k) force[j*3+k]+=-contribution[p*3+k];
        for(int k=0;k<n*3;++k) if(!std::isfinite(force[k])) return 3;
        return 0;
    } catch(...) { return 5; }
}

// Straight drift between two pair geometries. Nonrepresentable closest-point
// arithmetic is refused; no NaN comparison can silently miss an exclusion.
C2API int c2em_pair_crossing(int pairs, const double* start, const double* end,
    const double* exclusion) noexcept {
    if(pairs<0 || pairs>8128 || !start || !end || !exclusion) return 1;
    for(int p=0;p<pairs;++p) {
        const double* a=start+p*3;const double* b=end+p*3;
        const double dx=b[0]-a[0],dy=b[1]-a[1],dz=b[2]-a[2];
        const double length=(dx*dx+dy*dy)+dz*dz;
        const double dot=-((a[0]*dx+a[1]*dy)+a[2]*dz);
        if(!std::isfinite(length) || !std::isfinite(dot)) return 3;
        const double fraction=length!=0 ? std::clamp(dot/length,0.,1.) : 0.;
        const double cx=a[0]+fraction*dx,cy=a[1]+fraction*dy,cz=a[2]+fraction*dz;
        const double closest=std::sqrt((cx*cx+cy*cy)+cz*cz);
        if(!std::isfinite(closest)) return 3;
        if(closest<=exclusion[p]) return 2;
    }
    return 0;
}
