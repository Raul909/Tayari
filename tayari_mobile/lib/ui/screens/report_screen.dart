import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:geolocator/geolocator.dart';
import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import '../../models/report.dart';
import '../../providers/db_provider.dart';
import '../theme.dart';

class ReportScreen extends ConsumerStatefulWidget {
  final String basinId;
  const ReportScreen({super.key, required this.basinId});

  @override
  ConsumerState<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends ConsumerState<ReportScreen> {
  final ImagePicker _picker = ImagePicker();
  File? _imageFile;
  Position? _position;
  String _status = 'Water rising';
  bool _isSubmitting = false;

  Future<void> _takePhoto() => _pickImage(ImageSource.camera);

  Future<void> _pickFromGallery() => _pickImage(ImageSource.gallery);

  Future<void> _pickImage(ImageSource source) async {
    try {
      final XFile? photo = await _picker.pickImage(
        source: source,
        maxWidth: 1600,
        imageQuality: 85,
      );
      if (photo != null) {
        setState(() => _imageFile = File(photo.path));
        _getLocation(); // Capture location automatically alongside the photo
      }
    } catch (e) {
      _snack(
        source == ImageSource.camera
            ? 'Could not open the camera. Try "Choose from gallery" instead.'
            : 'Could not open the gallery: $e',
      );
    }
  }

  Future<void> _getLocation() async {
    if (!await Geolocator.isLocationServiceEnabled()) return;

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) return;
    }
    if (permission == LocationPermission.deniedForever) return;

    final position = await Geolocator.getCurrentPosition();
    if (mounted) setState(() => _position = position);
  }

  void _snack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _submitReport() async {
    if (_imageFile == null || _position == null) {
      _snack('Take a photo and allow location access first.');
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      // Compress aggressively for low-bandwidth areas (~100 kB target).
      final dir = await getApplicationDocumentsDirectory();
      final targetPath =
          '${dir.path}/compressed_${DateTime.now().millisecondsSinceEpoch}.jpg';

      final XFile? compressedFile = await FlutterImageCompress.compressAndGetFile(
        _imageFile!.path,
        targetPath,
        quality: 50,
        minWidth: 800,
        minHeight: 800,
      );

      // Save to the offline queue first, so nothing is lost without a signal.
      final report = CommunityReport()
        ..basinId = widget.basinId
        ..latitude = _position!.latitude
        ..longitude = _position!.longitude
        ..status = _status
        ..compressedPhotoPath = compressedFile?.path ?? _imageFile!.path
        ..createdAt = DateTime.now()
        ..isSynced = false;

      final isar = await ref.read(isarProvider.future);
      await isar.writeTxn(() async {
        await isar.communityReports.put(report);
      });

      // Try to upload right away; anything not sent stays queued for later.
      ref
          .read(syncServiceProvider.future)
          .then((service) => service.syncPendingReports());

      _snack('Report saved. It will upload as soon as there is a connection.');
      if (mounted) Navigator.pop(context);
    } catch (e) {
      _snack('Could not save the report: $e');
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Community report')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: _imageFile != null
                    ? Stack(
                        fit: StackFit.expand,
                        children: [
                          Image.file(_imageFile!, fit: BoxFit.cover),
                          Positioned(
                            right: 8,
                            bottom: 8,
                            child: ElevatedButton.icon(
                              onPressed: _takePhoto,
                              icon: const Icon(Icons.refresh, size: 16),
                              label: const Text('Retake'),
                            ),
                          ),
                        ],
                      )
                    : Container(
                        decoration: BoxDecoration(
                          color: AppColors.surfaceSunken,
                          border: Border.all(color: AppColors.border),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                icon: const Icon(Icons.camera_alt_outlined, size: 56),
                                color: AppColors.accent,
                                onPressed: _takePhoto,
                              ),
                              const Text(
                                'Take a photo of the conditions',
                                style: TextStyle(color: AppColors.textMuted),
                              ),
                              TextButton(
                                onPressed: _pickFromGallery,
                                child: const Text('or choose from gallery'),
                              ),
                            ],
                          ),
                        ),
                      ),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Icon(
                  _position != null ? Icons.location_on : Icons.location_searching,
                  size: 18,
                  color: _position != null ? AppColors.riskLow : AppColors.textMuted,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    _position != null
                        ? 'Location: ${_position!.latitude.toStringAsFixed(4)}, ${_position!.longitude.toStringAsFixed(4)}'
                        : 'Location will be captured with the photo',
                    style: TextStyle(
                      color: _position != null
                          ? AppColors.riskLow
                          : AppColors.textMuted,
                      fontSize: 13,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: _status,
              decoration: const InputDecoration(labelText: 'Current condition'),
              items: const [
                DropdownMenuItem(value: 'Water rising', child: Text('Water rising rapidly')),
                DropdownMenuItem(value: 'Road flooded', child: Text('Road is flooded')),
                DropdownMenuItem(value: 'All clear', child: Text('Water levels normal')),
              ],
              onChanged: (val) => setState(() => _status = val ?? _status),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: _isSubmitting ? null : _submitReport,
              child: _isSubmitting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Text('Save & sync report'),
            ),
          ],
        ),
      ),
    );
  }
}
