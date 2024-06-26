import math

import torch
import torch.autograd as autograd
import torch.distributions as dist

from importlib import reload

from _01_data_generation import generate_data
from _02_method import *
from _00_funcs import *
from _97_gpytorch import *


torch.manual_seed(1)

# generate data
dat = generate_data(250, 4)

dat["X"].dtype
dat["y"].dtype
dat["b"].dtype

# set prior params
mu = torch.zeros(4, dtype=torch.double)
sig = torch.ones(4, dtype=torch.double) * 4

# parameters of the variational distribution
m = torch.randn(4, requires_grad=True, dtype=torch.double)
u = torch.tensor([-1.,-1., -1., -1.], requires_grad=True, dtype=torch.double)
s = torch.exp(u)

t = torch.ones(250, dtype=torch.double, requires_grad=True)

# check if values of functions match
KL(m, s, mu, sig)
KL_MC(m, s, mu, sig)
d1 = dist.Normal(mu, sig)
d2 = dist.Normal(m, s)
torch.sum(torch.distributions.kl.kl_divergence(d2, d1))

# check for MultiVariateNormal
KL_mvn(m, torch.diag(s), mu, torch.diag(sig)) 
d1 = dist.MultivariateNormal(mu, torch.diag(sig))  
d2 = dist.MultivariateNormal(m, torch.diag(s))
torch.distributions.kl.kl_divergence(d2, d1)   


ELL_MC(m, s, dat["y"], dat["X"])
ELL_TB(m, s, dat["y"], dat["X"])
ELL_Jak(m, s, t, dat["y"], dat["X"])

ELBO_MC(m, s, dat["y"], dat["X"], mu, sig)
ELBO_TB(m, s, dat["y"], dat["X"], mu, sig)
ELBO_Jak(m, u, t, dat["y"], dat["X"], mu, sig)


autograd.gradcheck(ELBO_TB, (m, s, dat["y"], dat["X"], mu, sig)) 
autograd.gradcheck(ELBO_Jak, (m, s,t,  dat["y"], dat["X"], mu, sig)) 
autograd.gradcheck(ELBO_MC, (m, u, dat["y"], dat["X"], mu, sig)) 


from importlib import reload
import sys
reload(sys.modules["_02_method"])

dat = generate_data(1000, 25, dgp=2, seed=99)

f0 = LogisticVI(dat, method=0, intercept=False, verbose=True)
f0.fit()
f0.runtime

f0sgd = LogisticVI(dat, method=1, intercept=False, verbose=True, sgd=True, num_workers=1, batches=1, n_iter=61)
f0sgd.fit()
f0sgd.runtime


f1 = LogisticVI(dat, method=1, intercept=False, verbose=True, n_iter=1500)
f1.fit()
f1.runtime

f2 = LogisticVI(dat, method=2, intercept=False, verbose=True, n_iter=1500)
f2.fit()
f2.runtime

f3 = LogisticVI(dat, method=3, intercept=False, verbose=True, n_iter=1500)
f3.fit()
f3.runtime



f6 = LogisticMCMC(dat, intercept=False, n_iter=1000, burnin=500, verbose=True)
f6.fit()

from torch.profiler import profile, record_function, ProfilerActivity
f1 = LogisticVI(dat, method=1, intercept=False, verbose=True, n_iter=1500)

with profile(activities=[ProfilerActivity.CPU], record_shapes=True) as prof:
    with record_function("model_inference"):
        f1.fit()


print(prof.key_averages().table(sort_by="cpu_time_total", row_limit=10))



#
#
# 

def nb_2(m, s, l_max = 10.0):
    l = torch.arange(1.0, l_max*2, 1.0, requires_grad=False, dtype=torch.float64)
    l = l.unsqueeze(0)

    res = torch.sum(
            s / torch.sqrt(2.0 * torch.tensor(torch.pi)) * torch.exp(- 0.5 * m**2 / s**2) + \
            m * ndtr(m / s)
        ) + \
        torch.sum(
            (-1.0)**(l - 1.0) / l * (
                torch.exp( m @ l + 0.5 * s**2 @ (l ** 2) + log_ndtr(-m / s - s @ l)) + \
                torch.exp(-m @ l + 0.5 * s**2 @ (l ** 2) + log_ndtr( m / s - s @ l))
            )
        )
    return res


dat = generate_data(200, 5, dgp=2, seed=99)
f0 = LogisticVI(dat, method=0, intercept=False, verbose=True, l_max=12.0)
f0.fit()
evaluate_method(f0, dat)

f2 = LogisticVI(dat, method=2, intercept=False, verbose=True, l_max=12.0)
f2.fit()
evaluate_method(f2, dat)

f4 = LogisticVI(dat, method=4, intercept=False, verbose=True, l_max=12.0)
f4.fit()
evaluate_method(f4, dat)


f_pred = dat["X"] @ f0.sample(5000).t()
f_pred.mean(1).shape

f6 = LogisticMCMC(dat, intercept=False, n_iter=1000, burnin=500, verbose=True)
f6.fit()

f_pred = dat["X"] @ f6.B.t()
f_pred.mean(1).shape

evaluate_method(f6, dat, method="mcmc")


m = torch.tensor(-1.0, dtype=torch.double, requires_grad=True)
s = torch.tensor(2.0, dtype=torch.double, requires_grad=True)

nor = dist.Normal(m, s)
samp = nor.sample((5000, ))

plt.hist(torch.log1p(torch.exp(samp)).detach().numpy(), bins=100)
plt.show()

m = m.unsqueeze(0)
s = s.unsqueeze(0)

for l in range(1, 20):
    nb(m, s, l_max=l)

mc_est(m, s, n_samples=1000000)

res = []
res0 = []
for l in range(1, 20):
    m = torch.tensor(0.152, dtype=torch.double, requires_grad=True)
    s = torch.tensor(0.486, dtype=torch.double, requires_grad=True)
    r = nb(m, s, l_max=l)
    r.backward()
    res.append(s.grad.item())
    
    m = torch.tensor(0.155, dtype=torch.double, requires_grad=True)
    s = torch.tensor(0.498, dtype=torch.double, requires_grad=True)
    r = nb(m, s, l_max=l)
    r.backward()
    res0.append(s.grad.item())
    

plt.plot(range(1, 20), res)
plt.plot(range(1, 20), res0)
plt.show()

res

dat = generate_data(1000, 5, dgp=0, seed=9)
f = LogisticVI(dat, method=0, intercept=False, verbose=True, l_max=12.0)
f.fit()
evaluate_method(f, dat)




MM = dat["X"] @ f.m

plt.hist(MM.detach().numpy(), bins=100)
plt.show()

SS = dat["X"] ** 2 @ f.s**2
plt.hist(SS.detach().numpy(), bins=100)
plt.show()
SS.mean()
MM.mean()


torch.manual_seed(1)
p = 50
U = torch.rand(p, p, dtype=torch.double)
S = U @ U.t()
m = torch.rand(p, dtype=torch.double)

U = torch.rand(p, p, dtype=torch.double )
Sig = U @ U.t()
mu = torch.rand(p, dtype=torch.double)

m = torch.tensor(m, dtype=torch.float32)
S = torch.tensor(S, dtype=torch.float32)
Sig = torch.tensor(Sig, dtype=torch.float32)
mu = torch.tensor(mu, dtype=torch.float32)

print(torch.distributions.kl.kl_divergence(dist.MultivariateNormal(m, S), dist.MultivariateNormal(mu, Sig)))

KL_mvn(m, S, mu, Sig)

kl = 0.5 * (torch.logdet(Sig) - torch.logdet(S) - 10 + \
    torch.trace( torch.inverse(Sig) @ S) + \
    (mu - m) @ torch.inverse(Sig) @ (mu - m).t())
kl


func = lambda x: - 4.5 * torch.sin(math.pi / 2 * x)
# func = lambda x: torch.cos(x * math.pi / 2) * 2 + torch.cos(x)

n = 50
train_x = torch.cat((torch.linspace(0, 2.5, int(n / 2)), torch.linspace(3.5, 5, int(n / 2))))

train_f = func(train_x) + torch.randn(train_x.shape[0]) * 1.0 
train_x = train_x.reshape(-1, 1)
train_p = torch.sigmoid(train_f)
train_y = torch.bernoulli(train_p)
# 
test_x = torch.linspace(0, 5, 30)
test_f = func(test_x) + torch.randn(test_x.shape[0]) * 1.0  
test_p = torch.sigmoid((test_f))
test_y = torch.bernoulli(test_p)

xs = torch.linspace(0, 5, 100).reshape(-1, 1)
true_f = func(xs)

f0 = LogisticGPVI(train_y, train_x, n_inducing=50, n_iter=200, thresh=1e-6, verbose=True)
f0.fit()

f1 = LogisticGPVI(train_y, train_x, likelihood=LogitLikelihoodMC(1000), n_inducing=50, n_iter=200, thresh=1e-6, verbose=True)
f1.fit()

f2 = LogisticGPVI(train_y, train_x, likelihood=PGLikelihood(), n_inducing=50, n_iter=200, thresh=1e-6, verbose=True)
f2.fit()

import time

torch.manual_seed(1)
p = 20
U = torch.rand(p, p, dtype=torch.double)
S = U @ U.t()


dat = generate_data(20000, p, dgp=0, seed=9)
X = dat["X"]

s = time.time()
for i in range(1000):
    a = torch.sum(X * (S @ X.t()).t(), dim=1)
    a = (X.unsqueeze(1) @ S @ X.unsqueeze(2)).squeeze()
e = time.time()
print(e - s)


a = torch.sum(X * (S @ X.t()).t(), dim=1)
aa = (X.unsqueeze(1) @ S @ X.unsqueeze(2)).squeeze()

torch.allclose(a, aa)

(XX @ S @ XX.transpose(1, 2)).squeeze()
    
