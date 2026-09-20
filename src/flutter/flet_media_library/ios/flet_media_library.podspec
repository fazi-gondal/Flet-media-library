Pod::Spec.new do |s|
  s.name             = 'flet_media_library'
  s.version          = '0.1.0'
  s.summary          = 'Flet media library extension (photo_manager backend)'
  s.description      = <<-DESC
Flet service extension for device media library access. Native iOS work is
delegated to the photo_manager plugin; this pod only registers the package.
                       DESC
  s.homepage         = 'https://github.com/fazi-gondal/Flet-media-library'
  s.license          = { :type => 'MIT' }
  s.author           = { 'Fazi-Gondal' => 'nextinpk@gmail.com' }
  s.source           = { :path => '.' }
  s.source_files     = 'Classes/**/*'
  s.dependency 'Flutter'
  s.platform         = :ios, '12.0'
  s.swift_version    = '5.0'

  s.pod_target_xcconfig = {
    'DEFINES_MODULE' => 'YES',
    'EXCLUDED_ARCHS[sdk=iphonesimulator*]' => 'i386'
  }
end
