# -*- coding: utf-8 -*-
# coding: utf-8

import numpy as np
import torch
#import torchsnooper
import json


def confusion_matrix(y_pred, y_real):
    """Compute confusion matrix.

    Args:
        y_pred (list[int] | np.ndarray[int]): Prediction labels.
        y_real (list[int] | np.ndarray[int]): Ground truth labels.

    Returns:
        np.ndarray: Confusion matrix.
    """
    if isinstance(y_pred, list):
        y_pred = np.array(y_pred)
    if not isinstance(y_pred, np.ndarray):
        raise TypeError(
            f'y_pred must be list or np.ndarray, but got {type(y_pred)}')
    if not y_pred.dtype == np.int64:
        raise TypeError(
            f'y_pred dtype must be np.int64, but got {y_pred.dtype}')

    if isinstance(y_real, list):
        y_real = np.array(y_real)
    if not isinstance(y_real, np.ndarray):
        raise TypeError(
            f'y_real must be list or np.ndarray, but got {type(y_real)}')
    if not y_real.dtype == np.int64:
        raise TypeError(
            f'y_real dtype must be np.int64, but got {y_real.dtype}')

    label_set = np.unique(np.concatenate((y_pred, y_real)))
    print('label_set',label_set)
    num_labels = len(label_set)
    label_map = {label: i for i, label in enumerate(label_set)}
    confusion_mat = np.zeros((num_labels, num_labels), dtype=np.int64)
    for rlabel, plabel in zip(y_real, y_pred):
        index_real = label_map[rlabel]
        index_pred = label_map[plabel]
        confusion_mat[index_real][index_pred] += 1

    return confusion_mat


#@torchsnooper.snoop()
def mean_class_accuracy(scores, labels):
    """Calculate mean class accuracy.

    Args:
        scores (list[np.ndarray]): Prediction scores for each class.
        labels (list[int]): Ground truth labels.

    Returns:
        np.ndarray: Mean class accuracy.
    """
    
    pred = np.argmax(scores, axis=1)
    cf = confusion_matrix(pred, labels).astype(float)

    cls_cnt = cf.sum(axis=1)
    cls_hit = np.diag(cf)

    mean_class_acc = np.mean(
        [hit / cnt if cnt else 0.0 for cnt, hit in zip(cls_cnt, cls_hit)])

    return mean_class_acc

#@torchsnooper.snoop()
def personal_PR(scores, labels):
    """Calculate Percision/Recall.
       Save scores and labels.

    Args:
        scores (list[np.ndarray]): Prediction prob not scores for each class.
        labels (list[int]): Ground truth labels.

    Returns:
        np.ndarray: Percision for each class.
        np.ndarray: Recall for each class.
        np.ndarray: Mean class Percision.
        np.ndarray: Mean class Recall.
    """
    np.save("prob_scores_raw.npy",scores)
    for i in range(len(labels)):
        labels[i] = labels[i].numpy().tolist()
    y_true = np.array(labels)
    np.save("prob_y_true.npy",y_true)
    # top1 , get y_pred
    pred = np.argmax(scores, axis=1)
    y_pred = np.zeros_like(scores)
    for i in range(len(pred)):
        y_pred[i,pred[i]] = 1
    TP = np.sum(np.logical_and(np.equal(y_true, 1), np.equal(y_pred, 1)),axis=0) 
    FP = np.sum(np.logical_and(np.equal(y_true, 0), np.equal(y_pred, 1)),axis=0)  
    FN = np.sum(np.logical_and(np.equal(y_true, 1), np.equal(y_pred, 0)),axis=0)  
    P=TP/(TP+FP)
    R=TP/(TP+FN)
    TP = np.sum(np.logical_and(np.equal(y_true, 1), np.equal(y_pred, 1))) 
    FP = np.sum(np.logical_and(np.equal(y_true, 0), np.equal(y_pred, 1)))  
    FN = np.sum(np.logical_and(np.equal(y_true, 1), np.equal(y_pred, 0))) 
    total_P=TP/(TP+FP) 
    total_R=TP/(TP+FN) 
    return P, R, total_P, total_R


def top_k_accuracy(scores, labels, topk=(1, )):
    """Calculate top k accuracy score.

    Args:
        scores (list[np.ndarray]): Prediction scores for each class.
        labels (list[int]): Ground truth labels.
        topk (tuple[int]): K value for top_k_accuracy. Default: (1, ).

    Returns:
        list[float]: Top k accuracy score for each k.
    """
    res = []
    labels = np.array(labels)[:, np.newaxis]
    for k in topk:
        max_k_preds = np.argsort(scores, axis=1)[:, -k:][:, ::-1]
        match_array = np.logical_or.reduce(max_k_preds == labels, axis=1)
        topk_acc_score = match_array.sum() / match_array.shape[0]
        res.append(topk_acc_score)

    return res


def mean_average_precision(scores, labels):
    """Mean average precision for multi-label recognition.

    Args:
        scores (list[np.ndarray]): Prediction scores for each class.
        labels (list[np.ndarray]): Ground truth many-hot vector.

    Returns:
        np.float: The mean average precision.
    """
    results = []
    for i in range(len(scores)):
        precision, recall, _ = binary_precision_recall_curve(
            scores[i], labels[i])
        ap = -np.sum(np.diff(recall) * np.array(precision)[:-1])
        results.append(ap)
    return np.mean(results)


def binary_precision_recall_curve(y_score, y_true):
    """Calculate the binary precision recall curve at step thresholds.

    Args:
        y_score (np.ndarray): Prediction scores for each class.
            Shape should be (num_classes, ).
        y_true (np.ndarray): Ground truth many-hot vector.
            Shape should be (num_classes, ).

    Returns:
        precision (np.ndarray): The precision of different thresholds.
        recall (np.ndarray): The recall of different thresholds.
        thresholds (np.ndarray): Different thresholds at which precison and
            recall are tested.
    """
    assert isinstance(y_score, np.ndarray)
    assert isinstance(y_true, np.ndarray)
    assert y_score.shape == y_true.shape

    # make y_true a boolean vector
    y_true = (y_true == 1)
    # sort scores and corresponding truth values
    desc_score_indices = np.argsort(y_score, kind='mergesort')[::-1]
    y_score = y_score[desc_score_indices]
    y_true = y_true[desc_score_indices]
    # There may be ties in values, therefore find the `distinct_value_inds`
    distinct_value_inds = np.where(np.diff(y_score))[0]
    threshold_inds = np.r_[distinct_value_inds, y_true.size - 1]
    # accumulate the true positives with decreasing threshold
    tps = np.cumsum(y_true)[threshold_inds]
    fps = 1 + threshold_inds - tps
    thresholds = y_score[threshold_inds]

    precision = tps / (tps + fps)
    precision[np.isnan(precision)] = 0
    recall = tps / tps[-1]
    # stop when full recall attained
    # and reverse the outputs so recall is decreasing
    last_ind = tps.searchsorted(tps[-1])
    sl = slice(last_ind, None, -1)

    return np.r_[precision[sl], 1], np.r_[recall[sl], 0], thresholds[sl]


def pairwise_temporal_iou(candidate_segments, target_segments):
    """Compute intersection over union between segments.

    Args:
        candidate_segments (np.ndarray): 2-dim array in format
            [m x 2:=[init, end]].
        target_segments (np.ndarray): 2-dim array in format
            [n x 2:=[init, end]].

    Returns:
        temporal_iou (np.ndarray): 2-dim array [n x m] with IOU ratio.
    """
    if target_segments.ndim != 2 or candidate_segments.ndim != 2:
        raise ValueError('Dimension of arguments is incorrect')

    n, m = target_segments.shape[0], candidate_segments.shape[0]
    temporal_iou = np.empty((n, m))
    for i in range(m):
        candidate_segment = candidate_segments[i, :]
        tt1 = np.maximum(candidate_segment[0], target_segments[:, 0])
        tt2 = np.minimum(candidate_segment[1], target_segments[:, 1])
        # Intersection including Non-negative overlap score.
        segments_intersection = (tt2 - tt1).clip(0)
        # Segment union.
        segments_union = ((target_segments[:, 1] - target_segments[:, 0]) +
                          (candidate_segment[1] - candidate_segment[0]) -
                          segments_intersection)
        # Compute overlap as the ratio of the intersection
        # over union of two segments.
        temporal_iou[:, i] = (
            segments_intersection.astype(float) / segments_union)

    return temporal_iou


def average_recall_at_avg_proposals(ground_truth,
                                    proposals,
                                    total_num_proposals,
                                    max_avg_proposals=None,
                                    temporal_iou_thresholds=np.linspace(
                                        0.5, 0.95, 10)):
    """Computes the average recall given an average number (percentile)
    of proposals per video.

    Args:
        ground_truth (dict): Dict containing the ground truth instances.
        proposals (dict): Dict containing the proposal instances.
        total_num_proposals (int): Total number of proposals in the
            proposal dict.
        max_avg_proposals (int | None): Max number of proposals for one video.
            Default: None.
        temporal_iou_thresholds (np.ndarray): 1D array with temporal_iou
            thresholds. Default: np.linspace(0.5, 0.95, 10).

    Returns:
        recall (np.ndarray): recall[i,j] is recall at i-th temporal_iou
            threshold at the j-th average number (percentile) of average
            number of proposals per video.
        average_recall (np.ndarray): Recall averaged over a list of
            temporal_iou threshold (1D array). This is equivalent to
            recall.mean(axis=0).
        proposals_per_video (np.ndarray): Average number of proposals per
            video.
        auc (float): Area under AR@AN curve.
    """

    total_num_videos = len(ground_truth)

    if not max_avg_proposals:
        max_avg_proposals = float(total_num_proposals) / total_num_videos

    ratio = (max_avg_proposals * float(total_num_videos) / total_num_proposals)

    # For each video, compute temporal_iou scores among the retrieved proposals
    score_list = []
    total_num_retrieved_proposals = 0
    for video_id in ground_truth:
        # Get proposals for this video.
        proposals_video_id = proposals[video_id]
        this_video_proposals = proposals_video_id[:, :2]
        # Sort proposals by score.
        sort_idx = proposals_video_id[:, 2].argsort()[::-1]
        this_video_proposals = this_video_proposals[sort_idx, :].astype(
            np.float32)

        # Get ground-truth instances associated to this video.
        ground_truth_video_id = ground_truth[video_id]
        this_video_ground_truth = ground_truth_video_id[:, :2].astype(
            np.float32)
        if this_video_proposals.shape[0] == 0:
            n = this_video_ground_truth.shape[0]
            score_list.append(np.zeros((n, 1)))
            continue

        if this_video_proposals.ndim != 2:
            this_video_proposals = np.expand_dims(this_video_proposals, axis=0)
        if this_video_ground_truth.ndim != 2:
            this_video_ground_truth = np.expand_dims(
                this_video_ground_truth, axis=0)

        num_retrieved_proposals = np.minimum(
            int(this_video_proposals.shape[0] * ratio),
            this_video_proposals.shape[0])
        total_num_retrieved_proposals += num_retrieved_proposals
        this_video_proposals = this_video_proposals[:
                                                    num_retrieved_proposals, :]

        # Compute temporal_iou scores.
        temporal_iou = pairwise_temporal_iou(this_video_proposals,
                                             this_video_ground_truth)
        score_list.append(temporal_iou)

    # Given that the length of the videos is really varied, we
    # compute the number of proposals in terms of a ratio of the total
    # proposals retrieved, i.e. average recall at a percentage of proposals
    # retrieved per video.

    # Computes average recall.
    pcn_list = np.arange(1, 101) / 100.0 * (
        max_avg_proposals * float(total_num_videos) /
        total_num_retrieved_proposals)
    matches = np.empty((total_num_videos, pcn_list.shape[0]))
    positives = np.empty(total_num_videos)
    recall = np.empty((temporal_iou_thresholds.shape[0], pcn_list.shape[0]))
    # Iterates over each temporal_iou threshold.
    for ridx, temporal_iou in enumerate(temporal_iou_thresholds):
        # Inspect positives retrieved per video at different
        # number of proposals (percentage of the total retrieved).
        for i, score in enumerate(score_list):
            # Total positives per video.
            positives[i] = score.shape[0]
            # Find proposals that satisfies minimum temporal_iou threshold.
            true_positives_temporal_iou = score >= temporal_iou
            # Get number of proposals as a percentage of total retrieved.
            pcn_proposals = np.minimum(
                (score.shape[1] * pcn_list).astype(np.int), score.shape[1])

            for j, num_retrieved_proposals in enumerate(pcn_proposals):
                # Compute the number of matches
                # for each percentage of the proposals
                matches[i, j] = np.count_nonzero(
                    (true_positives_temporal_iou[:, :num_retrieved_proposals]
                     ).sum(axis=1))

        # Computes recall given the set of matches per video.
        recall[ridx, :] = matches.sum(axis=0) / positives.sum()

    # Recall is averaged.
    avg_recall = recall.mean(axis=0)

    # Get the average number of proposals per video.
    proposals_per_video = pcn_list * (
        float(total_num_retrieved_proposals) / total_num_videos)
    # Get AUC
    area_under_curve = np.trapz(avg_recall, proposals_per_video)
    auc = 100. * float(area_under_curve) / proposals_per_video[-1]
    return recall, avg_recall, proposals_per_video, auc
