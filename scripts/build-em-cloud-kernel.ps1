param()
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$source=Join-Path $root 'output/c212-em-cloud-native-staging'
$build=Join-Path $root 'build/em-cloud-native'
$cmake=Join-Path $root '.tooling/python/Scripts/cmake.exe'
& $cmake -S $source -B $build -G 'Visual Studio 17 2022' -A x64 "-DCMAKE_GENERATOR_INSTANCE=$root/.tooling/vs-buildtools"
if($LASTEXITCODE -ne 0){throw 'EM cloud configuration failed'}
& $cmake --build $build --config Release --parallel 1
if($LASTEXITCODE -ne 0){throw 'EM cloud build failed'}
$compiler=Join-Path $root '.tooling/vs-buildtools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/cl.exe'
$dll=Join-Path $build 'Release/cosmos2_em_cloud.dll'
$receipt=@{schema=1;abi=1;compiler=$compiler;compiler_sha256=(Get-FileHash $compiler -Algorithm SHA256).Hash.ToLowerInvariant();
  dll_sha256=(Get-FileHash $dll -Algorithm SHA256).Hash.ToLowerInvariant();
  cpp_sha256=(Get-FileHash "$source/cloud_kernel.cpp" -Algorithm SHA256).Hash.ToLowerInvariant();
  cmake_sha256=(Get-FileHash "$source/CMakeLists.txt" -Algorithm SHA256).Hash.ToLowerInvariant();
  builder_sha256=(Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant();
  policy='MSVC x64 Release /O2 /fp:strict /arch:AVX2 /openmp; CPUID/OS support checked;4 independent SIMD lanes with fixed source order and compensated sums per particle;1..8 caller-selected threads; no approximate reciprocal, fast math or FMA. Experimental helper, no scientific/native acceptance.'}
$receipt | ConvertTo-Json | Set-Content "$source/build-receipt.json" -Encoding UTF8
Copy-Item $dll "$source/cosmos2_em_cloud.dll" -Force
$receipt | ConvertTo-Json
