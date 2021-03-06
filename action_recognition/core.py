# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/00_core.ipynb (unless otherwise specified).

__all__ = ['PATH', 'IMAGE_PATH', 'SPLIT_PATH', 'get_sequence_paths', 'ImageTuple', 'ImageTupleBlock', 'get_tuple_files',
           'make_sequences', 'sort_files', 'ActionDataset', 'TupleImage', 'ImageTupleTfm', 'get_split',
           'get_split_idxs', 'get_action_dataloaders', 'grand_parent_label', 'get_block']

# Cell
from fastai.vision.all import *

# Cell
PATH = Path.cwd().parent/'data'
Path.BASE_PATH = PATH

IMAGE_PATH = PATH/'UCF-101-frames'
SPLIT_PATH = PATH/'ucfTrainTestlist'

# Cell
def get_sequence_paths(path):
    " gets all sequences folders paths"
    sequence_paths = []
    for actions in path.ls():
        sequence_paths += actions.ls()
    return sequence_paths

# Cell
class ImageTuple(fastuple):
    "An Image tuple class of arbitrary lenght"
    @classmethod
    def create(cls, fns):
        return cls(tuple(PILImage.create(f) for f in fns))

    def show(self, ctx=None, **kwargs):
        "shows 1st middle and last images of the seq"
        n = len(self)
        for t in self:
            if not isinstance(t, Tensor):
                return ctx
        return show_image(torch.cat((self[0], self[n//2], self[-1]) , dim=2), ctx=ctx, figsize=(6,3),**kwargs)

# Cell
def ImageTupleBlock(): return TransformBlock(type_tfms=ImageTuple.create, batch_tfms=IntToFloatTensor)

# Cell
def get_tuple_files(files):
    "Get a list of tuple paths"
    def sort_sequence(seq_path):
        return L(seq_path.ls().sorted(key=lambda f: int(f.with_suffix('').name)))
    return files.map(sort_sequence)

# Cell
def make_sequences(tuples_files, seq_len=40):
    "slice sequences to `seq_len`"
    return L(tups[0:seq_len] for tups in tuples_files)

# Cell
def sort_files(path_seq):
    return path_seq.sorted(key=lambda f: int(f.with_suffix('').name))

# Cell
class ActionDataset():
    "A wrapper to hold the data on path format"
    def __init__(self, image_path, random_sample=False, seq_len=20):
        self.sequence_paths = get_sequence_paths(image_path)
        self.tuples_files = get_tuple_files(self.sequence_paths) if not random_sample else None
        self.seq_len = seq_len
        self.random_sample = random_sample

    def __getitem__(self, i):
        "Get a list of images files for item i"
        label = self.sequence_paths[i].parent.name
        if self.random_sample:
            frames = self.sequence_paths[i].ls()
            return tuple(PILImage.create(f) for f in sort_files(L(random.sample(list(frames), self.seq_len))))+(Category(label),)
        else:
            frames = self.tuples_files[i]
            n_frames = len(frames)
            first_idx = random.randint(0, n_frames-self.seq_len)
            s = slice(first_idx, first_idx+self.seq_len)
            return tuple(PILImage.create(f) for f in frames[s])+(Category(label),)

    def __len__(self):
        return len(self.sequence_paths)

# Cell
class TupleImage(fastuple):
    "A tuple of PILImages"
    def show(self, ctx=None, **kwargs):
        n = len(self)
        img0, img1, img2= self[0], self[n//2], self[n-2]
        if not isinstance(img1, Tensor):
            t0, t1,t2 = tensor(img0), tensor(img1),tensor(img2)
            t0, t1,t2 = t0.permute(2,0,1), t1.permute(2,0,1),t2.permute(2,0,1)
        else: t0, t1,t2 = img0, img1,img2
        return show_image(torch.cat([t0,t1,t2], dim=2), ctx=ctx, **kwargs)

# Cell
class ImageTupleTfm(Transform):
    "A wrapper to hold the data on path format"
    def __init__(self, random_sample=False, seq_len=20):
        self.seq_len = seq_len
        self.random_sample = random_sample

    def encodes(self, path):
        "Get a list of images files for folder path"
        if self.random_sample:
            frames = path.ls()
            return TupleImage(tuple(PILImage.create(f) for f in sort_files(L(random.sample(list(frames), self.seq_len)))))
        else:
            frames = sort_files(path.ls())
            n_frames = len(frames)
            first_idx = random.randint(0, n_frames-self.seq_len)
            s = slice(first_idx, first_idx+self.seq_len)
            return TupleImage(tuple(PILImage.create(f) for f in frames[s]))

# Cell
def get_split(split_file=SPLIT_PATH/'testlist01.txt', image_path=IMAGE_PATH):
    "return split from file"
    return L(image_path/(Path(f)).with_suffix('') for f in pd.read_csv(split_file, header=None, names=['fname']).fname)

# Cell
def get_split_idxs(split_file=SPLIT_PATH/'testlist01.txt', image_path=IMAGE_PATH):
    "return indexes of split_list on files"
    split_list = get_split(split_file, image_path)
    files = get_sequence_paths(image_path)
    return [i for i,x in enumerate(files) if x in split_list]

# Cell
def get_action_dataloaders(files, bs=8, image_size=64, seq_len=20, val_idxs=None, random_sample=False, **kwargs):
    "Create a dataloader with `val_idxs` splits"
    splits = RandomSplitter()(files) if val_idxs is None else IndexSplitter(val_idxs)(files)
    itfm = ImageTupleTfm(random_sample=random_sample, seq_len=seq_len)
    ds = Datasets(files, tfms=[[itfm], [parent_label, Categorize]], splits=splits)
    dls = ds.dataloaders(bs=bs, after_item=[Resize(image_size), ToTensor],
                         after_batch=[IntToFloatTensor, Normalize.from_stats(*imagenet_stats)], drop_last=True, **kwargs)
    return dls

# Cell
def grand_parent_label(o, **kwargs):
    "Label `item` with the gparent folder name."
    return o[0].parent.parent.name

# Cell
def get_block(image_size=64, seq_len=40, val_idxs=None):
    "A block for sequence of images from file path list"
    item_tfms = [] if (image_size == None) else [Resize(image_size)]
    block = DataBlock(blocks    = (ImageTupleBlock, CategoryBlock),
                      get_items = partial(make_sequences, seq_len=seq_len),
                      get_y     = grand_parent_label,
                      item_tfms = item_tfms,
                      splitter  = IndexSplitter(val_idxs),
                      batch_tfms=[Normalize.from_stats(*imagenet_stats)])
    return block

# Cell
@typedispatch
def show_batch(x:ImageTuple, y, samples, ctxs=None, max_n=6, nrows=None, ncols=2, figsize=None, **kwargs):
    if figsize is None: figsize = (ncols*6, max_n//ncols * 3)
    if ctxs is None: ctxs = get_grid(min(len(samples), max_n), nrows=nrows, ncols=ncols, figsize=figsize)
    ctxs = show_batch[object](x, y, samples, ctxs=ctxs, max_n=max_n, **kwargs)
    return ctxs