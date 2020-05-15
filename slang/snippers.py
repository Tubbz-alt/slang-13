from typing import Callable
from slang.chunkers import fixed_step_chunker
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from slang.snip_stats import BayesFactors
from slang.core import Snipper


class DfltWfToChk:
    def __init__(self, chk_size=2048, chk_step=None):
        if chk_step is None:
            chk_step = chk_size
        self.chk_size = chk_size
        self.chk_step = chk_step

    def fit(self, *args, **kwargs):
        return self  # no fitting required

    def __call__(self, wf):
        yield from fixed_step_chunker(wf, chk_size=self.chk_size, chk_step=self.chk_step)


class DfltChkToFv(PCA):
    def __init__(self, n_components=5, *args, **kwargs):
        super().__init__(n_components=n_components, *args, **kwargs)

    def __call__(self, fv):
        return self.transform([fv])[0]


class DfltFvToSnip(KMeans):
    def __init__(self, n_clusters=47, *args, **kwargs):
        super().__init__(n_clusters=n_clusters, *args, **kwargs)

    def __call__(self, fv):
        return self.predict([fv])[0]


from collections.abc import Iterable


def is_iterable(x):
    """Similar in nature to :func:`callable`, ``is_iterable`` returns
    ``True`` if an object is `iterable`_, ``False`` if not.
    >>> is_iterable([])
    True
    >>> is_iterable(1)
    False"""
    return isinstance(x, Iterable)


def _get_pairs(iterables):
    """ """
    if hasattr(iterables, '__len__'):
        if len(iterables) == 2:
            return iterables
        elif len(iterables) == 1 and is_iterable(iterables[0]):
            return list(zip(*iterables[0]))
    else:
        return list(zip(*iterables))


def _is_a_tuple_of_aligned_iterables(x):
    return hasattr(x, '__len__') and len(x) == 2


def iterate_over_pairs(pairs):
    if _is_a_tuple_of_aligned_iterables(pairs):
        yield from zip(*pairs)
    else:
        yield from pairs  # assume pairs is an iterable of pairs


class ClassificationSnipper(Snipper):
    wf_to_chks: Callable
    chk_to_fv: Callable  # TODO: Make a "Callable and Fittable" type
    fv_to_snip: Callable  # TODO: Make a "Callable and Fittable" type
    snip_to_score: Callable  # TODO: Make a "Callable and Fittable" type

    dflt_cls_of_name = {
        'wf_to_chks': DfltWfToChk,
        'chk_to_fv': DfltChkToFv,
        'fv_to_snip': DfltFvToSnip,
        'snip_to_score': BayesFactors
    }

    @classmethod
    def mk_component(cls, obj, role=None, assert_func=None):
        if isinstance(obj, type):
            obj = obj()
        elif not callable(obj):
            assert isinstance(obj, dict)
            obj = cls.dflt_cls_of_name.get(role)(**obj)
        else:
            pass  # as is
        if assert_func is not None:
            assert assert_func(obj)
        return obj

    def __init__(self, wf_to_chks=DfltWfToChk(),
                 chk_to_fv=DfltChkToFv,
                 fv_to_snip=DfltFvToSnip,
                 snip_to_score=BayesFactors):

        wf_to_chks = self.mk_component(wf_to_chks, 'wf_to_chks', assert_func=callable)
        chk_to_fv = self.mk_component(chk_to_fv, 'chk_to_fv', assert_func=callable)
        fv_to_snip = self.mk_component(fv_to_snip, 'fv_to_snip', assert_func=callable)
        snip_to_score = self.mk_component(snip_to_score, 'snip_to_score', assert_func=callable)

        super().__init__(wf_to_chks, chk_to_fv, fv_to_snip)
        self.snip_to_score = snip_to_score

        # TODO: Find a more concise way to take care of block above. Like... (but not working)
        # _locals = locals()
        # for obj_role in ['wf_to_chks', 'chk_to_fv', 'fv_to_snip', 'snip_to_score']:
        #     _locals[obj_role] = self.mk_component(_locals[obj_role], obj_role, assert_func=callable)

    # TODO: Make the next four methods more DRY
    def fit_wf_to_chks(self, *chks_tags):
        if hasattr(self.wf_to_chks, 'fit'):
            chks, tags = _get_pairs(chks_tags)  # need to generalize to situations with no tags
            self.wf_to_chks.fit(chks, tags)
        return self

    def fit_chk_to_fv(self, *chks_tags):
        if hasattr(self.chk_to_fv, 'fit'):
            chks, tags = _get_pairs(chks_tags)
            self.chk_to_fv.fit(chks, tags)
        return self

    def fit_fv_to_snip(self, *fvs_tags):
        if hasattr(self.fv_to_snip, 'fit'):
            fvs, tags = _get_pairs(fvs_tags)
            self.fv_to_snip.fit(fvs, tags)
        return self

    def fit_snip_to_score(self, *snips_tags):
        if hasattr(self.snip_to_score, 'fit'):
            snips, tags = _get_pairs(snips_tags)
            self.snip_to_score.fit(snips, tags)
        return self

    # def snips_of_wf(self, wf: Waveform) -> Snips:
    #     warn("The name 'snips_of_wf' be replaced by 'wf_to_snips' soon.")
    #     for chk in self.wf_to_chks(wf):
    #         fv = self.chk_to_fv(chk)
    #         yield self.fv_to_snip(fv)
    #
    # def wf_to_fvs(self, wf: Waveform) -> FVs:
    #     for chk in self.wf_to_chks(wf):
    #         yield self.chk_to_fv(chk)
    #
    # def chk_to_snip(self, chk: Chunk) -> Snip:
    #     return self.fv_to_snip(self.chk_to_fv(chk))
    #
    # def wf_to_snips(self, wf: Waveform) -> Snips:
    #     for chk in self.wf_to_chks(wf):
    #         fv = self.chk_to_fv(chk)
    #         yield self.fv_to_snip(fv)


SlangClassifier = ClassificationSnipper  # alias for back compatibility