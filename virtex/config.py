from typing import Any, List, Optional

from fvcore.common.config import CfgNode as CN


class Config(object):
    r"""
    This class provides package-wide configuration management. It is a
    nested dict-like structure with nested keys accessible as attributes. It
    contains sensible default values, which can be modified by (first) a YAML
    file and (second) a list of attributes and values.

    An instantiated object is immutable: modifying any attribute is illegal.
    You must override required parameter values either through ``config_file``
    or ``override_list`` arguments. For adding more parameters at runtime
    (based on existing parameters), modify :meth:`add_derived_params`.

    Parameters
    ----------
    config_file: str
        Path to a YAML file containing configuration parameters to override.
    config_override: List[Any], optional (default = [])
        A list of sequential attributes and values of parameters to override.
        This happens after overriding from YAML file.

    Examples
    --------
    Let a YAML file named "config.yaml" specify these parameters to override::

        OPTIM:
          BATCH_SIZE: 512
          LR: 0.01

    >>> _C = Config("config.yaml", ["OPTIM.BATCH_SIZE", 1024])
    >>> _C.LR  # default: 0.001
    0.01
    >>> _C.OPTIM.BATCH_SIZE  # default: 256, file: 512
    1024
    """

    def __init__(
        self, config_file: Optional[str] = None, override_list: List[Any] = []
    ):
        _C = CN()

        # Random seed for NumPy and PyTorch, important for reproducibility.
        _C.RANDOM_SEED = 0
        # Train with Automatic Mixed Precision (native PyTorch).
        _C.AMP = True
        # Set CUDNN deterministic flag (torch.backends.cudnn.deterministic).
        # Setting this will ensure exact results on every run at the cost of
        # little slowdown. Good for debugging.
        _C.CUDNN_DETERMINISTIC = False
        # Set CUDNN benchmark flag (torch.backends.cudnn.benchmark). Enables
        # CUDNN to select fastest implementation for operations based on GPU.
        # May change results (in decimals) on different hardware, but faster
        # to train. Turn off while debugging.
        _C.CUDNN_BENCHMARK = True

        # ---------------------------------------------------------------------
        #   Data paths and parameters related to dataloading.
        # ---------------------------------------------------------------------
        _C.DATA = CN()

        # Path to the dataset root, which structure as per README. Path is
        # assumed to be relative to project root.
        _C.DATA.ROOT = "datasets/coco"
        # Path to .model file generated by ``sentencepiece``.
        _C.DATA.TOKENIZER_MODEL = "datasets/vocab/coco_10k.model"

        # Handy config params for vocab size and indices of special tokens.
        # While these can be picked up from the tokenizer, having these in
        # the config makes it easy to create a model without instantiating too
        # many tokenizer instances (especially when not needed, e.g. model zoo).
        # These must match according to what's present in ``TOKENIZER_VOCAB``
        # and ``TOKENIZER_MODEL`` above.
        _C.DATA.VOCAB_SIZE = 10000
        # Index of out-of-vocabulary (and padding) token.
        _C.DATA.UNK_INDEX = 0
        # Index of the start-of-sentence [SOS] token.
        _C.DATA.SOS_INDEX = 1
        # Index of the end-of-sentence [EOS] token.
        _C.DATA.EOS_INDEX = 2
        # Index of the word masking token. While not used for captioning, having
        # this extra token makes it possible to train an MLM model without
        # re-creating a new vocab mapping.
        _C.DATA.MASK_INDEX = 3

        # Size of the image (square) to crop from original input image.
        _C.DATA.IMAGE_CROP_SIZE = 224
        # Maximum length of input caption (number of tokens).
        # Longer captions will be truncated up to this length.
        _C.DATA.MAX_CAPTION_LENGTH = 30

        # List of image transforms (pre-processing and data augmentation) to be
        # applied sequentially (always or randomly) during training and
        # validation. Refer ``virtex/facetories.py`` for all possible transforms.
        _C.DATA.IMAGE_TRANSFORM_TRAIN = [
            "random_resized_crop",
            "horizontal_flip",
            "color_jitter",
            "normalize",
        ]
        _C.DATA.IMAGE_TRANSFORM_VAL = [
            "smallest_resize",
            "center_crop",
            "normalize",
        ]

        # Hyper-parameters for masked LM pretraining task. These are only used
        # when ``MODEL.NAME`` is "masked_lm".
        _C.DATA.MASKED_LM = CN()
        # Fraction of tokens to choose for masking, this must be less than 1.
        _C.DATA.MASKED_LM.MASK_PROPORTION = 0.15
        # Probability to replace chosen tokens with [MASK] token.
        _C.DATA.MASKED_LM.MASK_PROBABILITY = 0.85
        # Probability to replace chosen tokens with a random token.
        _C.DATA.MASKED_LM.REPLACE_PROBABILITY = 0.10

        # ---------------------------------------------------------------------
        #   Model architecture: visual backbone and textual head.
        # ---------------------------------------------------------------------
        _C.MODEL = CN()

        # Name of model, based on pretraining task.
        # Possible choices: {"token_classification", "multilabel_classification",
        # "captioning", "bicaptioning", "masked_lm", "virtex"}
        _C.MODEL.NAME = "virtex"

        _C.MODEL.VISUAL = CN()
        # Name of visual backbone. Possible choices: {"blind", "torchvision"}
        # Models from torchvision can be specified as shown below.
        _C.MODEL.VISUAL.NAME = "torchvision::resnet50"
        # Number of channels in pooled spatial features of visual backbone.
        _C.MODEL.VISUAL.FEATURE_SIZE = 2048
        # Whether to load ImageNet pretrained weights into visual backbone.
        _C.MODEL.VISUAL.PRETRAINED = False
        # Whether to keep visual backbone frozen and train only textual head.
        _C.MODEL.VISUAL.FROZEN = False

        _C.MODEL.TEXTUAL = CN()
        # Name of textual head. Set to "none" for MODEL.NAME = "*_classification".
        # Possible choices: {"transdec_postnorm", "transdec_prenorm"}.
        # Architectural hyper-parameters are specified as shown above.
        _C.MODEL.TEXTUAL.NAME = "transdec_postnorm::L1_H2048_A32_F8192"
        # L = Number of layers in the transformer.
        # H = Hidden size of the transformer (embeddings, attention features).
        # A = Number of attention heads in the transformer.
        # F = Size of feedforward layers in the transformer.
        # Typically, we have (A = H / 64) and (F = 4 * H).

        # Dropout probability for embedding, hidden features in textual head.
        _C.MODEL.TEXTUAL.DROPOUT = 0.1

        _C.MODEL.DECODER = CN()
        # What algorithm to use for decoding. Supported values: {"beam_search",
        # "nucleus_sampling"}.
        _C.MODEL.DECODER.NAME = "beam_search"
        # Number of beams to decode (1 = greedy decoding). Ignored when decoding
        # through nucleus sampling.
        _C.MODEL.DECODER.BEAM_SIZE = 5
        # Size of nucleus for sampling predictions. Ignored when decoding through
        # beam search.
        _C.MODEL.DECODER.NUCLEUS_SIZE = 0.9
        # Maximum length of decoded caption. Decoding may end earlier when [EOS]
        # token is sampled.
        _C.MODEL.DECODER.MAX_DECODING_STEPS = _C.DATA.MAX_CAPTION_LENGTH

        # ---------------------------------------------------------------------
        #   Optimization hyper-parameters, default values are for pretraining
        #   our best model on bicaptioning task (COCO Captions).
        # ---------------------------------------------------------------------
        _C.OPTIM = CN()

        # Name of optimizer to use. Supported values: {"sgd", "adamw"}.
        # AdamW uses default (beta1, beta2) values from PyTorch.
        _C.OPTIM.OPTIMIZER_NAME = "sgd"
        # Momentum co-efficient for SGD. Ignored for AdamW.
        _C.OPTIM.SGD_MOMENTUM = 0.9
        # Weight decay co-efficient for the optimizer.
        _C.OPTIM.WEIGHT_DECAY = 0.0001
        # Regex pattern of params for which there will be no weight decay.
        _C.OPTIM.NO_DECAY = ".*textual.(embedding|transformer).*(norm.*|bias)"
        # Max gradient norm for clipping to avoid exploding gradients.
        _C.OPTIM.CLIP_GRAD_NORM = 10.0

        # Wrap our optimizer with Lookahead (https://arxiv.org/abs/1907.08610).
        _C.OPTIM.LOOKAHEAD = CN()
        _C.OPTIM.LOOKAHEAD.USE = True
        _C.OPTIM.LOOKAHEAD.ALPHA = 0.5
        _C.OPTIM.LOOKAHEAD.STEPS = 5

        # We set different learning rates for CNN (visual backbone) and rest of
        # the model. CNN LR is typically much higher for training from scratch.
        # Both LRs undergo same warmup-decay schedules.

        # Total batch size (will be distributed evenly across GPUs).
        _C.OPTIM.BATCH_SIZE = 256
        # Max learning rate for CNN (visual backbone).
        _C.OPTIM.CNN_LR = 0.2
        # Max learning rate for rest of the model.
        _C.OPTIM.LR = 0.001
        # Number of iterations to train for, batches are randomly sampled.
        _C.OPTIM.NUM_ITERATIONS = 500000

        # Number of steps at the start of training for linear LR warmup.
        _C.OPTIM.WARMUP_STEPS = 10000
        # Learning rate annealing schedule for decay after warmup.
        # Possible choices: {"none", "linear", "cosine", "multistep"}.
        _C.OPTIM.LR_DECAY_NAME = "cosine"
        # Steps to decay LR for "multistep" schedule.
        _C.OPTIM.LR_STEPS = []
        # Factor to multiply with LR for "multistep" schedule.
        _C.OPTIM.LR_GAMMA = 0.1

        # Override parameter values from YAML file first, then from override
        # list, then add derived params.
        self._C = _C
        if config_file is not None:
            self._C.merge_from_file(config_file)
        self._C.merge_from_list(override_list)

        self.add_derived_params()

        # Make an instantiated object of this class immutable.
        self._C.freeze()

    def add_derived_params(self):
        r"""Add parameters with values derived from existing parameters."""

        # We don't have any such cases so far.
        pass

    def dump(self, file_path: str):
        r"""Save config at the specified file path.

        Parameters
        ----------
        file_path: str
            (YAML) path to save config at.
        """
        self._C.dump(stream=open(file_path, "w"))

    def __getattr__(self, attr: str):
        return self._C.__getattr__(attr)

    def __str__(self):
        return self._C.__str__()

    def __repr__(self):
        return self._C.__repr__()
